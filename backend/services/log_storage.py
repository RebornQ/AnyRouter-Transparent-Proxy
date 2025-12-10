"""
日志持久化存储模块

负责将实时日志写入本地 JSON Lines 文件，并提供历史查询能力
"""

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """确保 datetime 为 UTC 时区，便于比较"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class LogStorage:
    """按日分片的日志存储"""

    def __init__(self, storage_path: str = "logs", daily_limit: int = 1000, retention_days: int = 7):
        self.storage_path = storage_path
        self.daily_limit = daily_limit
        self.retention_days = retention_days
        self._lock = asyncio.Lock()
        self._daily_counts: Dict[str, int] = {}
        self._last_cleanup: Optional[datetime] = None

        os.makedirs(self.storage_path, exist_ok=True)

    def _get_file_path(self, dt: datetime) -> Tuple[str, str]:
        date_str = dt.strftime("%Y-%m-%d")
        file_name = f"{date_str}.jsonl"
        return os.path.join(self.storage_path, file_name), date_str

    async def _get_daily_count(self, date_str: str, file_path: str) -> int:
        if date_str in self._daily_counts:
            return self._daily_counts[date_str]

        def count_lines() -> int:
            if not os.path.exists(file_path):
                return 0
            with open(file_path, "r", encoding="utf-8") as f:
                return sum(1 for _ in f)

        count = await asyncio.to_thread(count_lines)
        self._daily_counts[date_str] = count
        return count

    async def _append_line(self, file_path: str, content: str) -> None:
        def write() -> None:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(content + "\n")

        await asyncio.to_thread(write)

    async def _maybe_cleanup(self) -> None:
        now = datetime.now(timezone.utc)
        if self._last_cleanup and (now - self._last_cleanup) < timedelta(hours=1):
            return

        self._last_cleanup = now
        cutoff = now - timedelta(days=self.retention_days)

        def cleanup_files() -> List[str]:
            removed: List[str] = []
            for name in os.listdir(self.storage_path):
                if not name.endswith(".jsonl"):
                    continue
                path = os.path.join(self.storage_path, name)
                try:
                    file_date = datetime.strptime(name.replace(".jsonl", ""), "%Y-%m-%d").replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
                if file_date < cutoff:
                    os.remove(path)
                    removed.append(name)
            return removed

        removed_files = await asyncio.to_thread(cleanup_files)
        if removed_files:
            for name in removed_files:
                self._daily_counts.pop(name.replace(".jsonl", ""), None)

    async def write_log(self, log_entry: dict) -> None:
        """写入单条日志，超出每日上限则静默丢弃"""
        timestamp = log_entry.get("timestamp")
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).timestamp()

        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        file_path, date_str = self._get_file_path(dt)

        # 确保格式化时间存在，便于前端直接使用
        enriched_entry = {**log_entry, "timestamp": timestamp}
        enriched_entry.setdefault("formatted_time", dt.astimezone().strftime("%Y-%m-%d %H:%M:%S"))

        async with self._lock:
            count = await self._get_daily_count(date_str, file_path)
            if count >= self.daily_limit:
                return
            self._daily_counts[date_str] = count + 1

        await self._append_line(file_path, json.dumps(enriched_entry, ensure_ascii=False))
        await self._maybe_cleanup()

    async def query_logs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        filters: Optional[Dict[str, str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[dict], int]:
        """按时间与过滤条件查询日志，返回分页结果"""
        filters = filters or {}
        level_filter = filters.get("level")
        path_filter = filters.get("path_filter")

        start_utc = _ensure_utc(start_time)
        end_utc = _ensure_utc(end_time)

        def read_all_entries() -> List[dict]:
            entries: List[dict] = []
            for name in sorted(os.listdir(self.storage_path)):
                if not name.endswith(".jsonl"):
                    continue
                path = os.path.join(self.storage_path, name)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                entries.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue
                except FileNotFoundError:
                    continue
            return entries

        raw_entries = await asyncio.to_thread(read_all_entries)
        filtered_entries: List[dict] = []

        for entry in raw_entries:
            ts = entry.get("timestamp")
            if ts is None:
                continue

            ts_dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            if start_utc and ts_dt < start_utc:
                continue
            if end_utc and ts_dt > end_utc:
                continue
            if level_filter and entry.get("level") != level_filter.upper():
                continue
            if path_filter and path_filter.lower() not in (entry.get("path") or "").lower():
                continue

            filtered_entries.append(entry)

        filtered_entries.sort(key=lambda e: e.get("timestamp", 0), reverse=True)
        total = len(filtered_entries)
        return filtered_entries[offset:offset + limit], total

    async def get_recent_logs(self, limit: int = 20) -> List[dict]:
        """获取最近的日志，按时间倒序排列"""
        entries, _ = await self.query_logs(limit=limit, offset=0)
        return entries

    async def rotate_files(self) -> None:
        """预留接口：当前按日期命名直接追加，无需显式轮转"""
        return None

    async def cleanup_old_files(self, days: int = 30) -> None:
        """手动触发清理"""
        self.retention_days = days
        await self._maybe_cleanup()

    async def clear_all(self) -> None:
        """清空所有持久化日志"""
        def remove_files():
            for name in os.listdir(self.storage_path):
                if not name.endswith(".jsonl"):
                    continue
                path = os.path.join(self.storage_path, name)
                try:
                    os.remove(path)
                except FileNotFoundError:
                    continue

        async with self._lock:
            await asyncio.to_thread(remove_files)
            self._daily_counts = {}
            self._last_cleanup = None
