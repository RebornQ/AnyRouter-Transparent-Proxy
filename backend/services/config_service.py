"""
配置管理服务模块

负责安全的 .env 文件读写操作，包括原子写入、备份机制和文件锁安全
"""

import asyncio
import errno
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from fcntl import flock, LOCK_EX, LOCK_UN, LOCK_NB
from dotenv import dotenv_values, set_key


class ConfigServiceError(Exception):
    """配置服务异常"""
    pass


class ConfigService:
    """
    配置管理服务

    提供安全的 .env 文件操作，包括：
    - 原子写入操作
    - 自动备份机制
    - 文件锁并发安全
    - 格式保持和注释保护
    """

    def __init__(self, env_file: str = ".env", backup_dir: str = "backups"):
        """
        初始化配置服务

        Args:
            env_file: .env 文件路径
            backup_dir: 备份目录路径
        """
        self.env_file = Path(env_file)
        self.backup_dir = Path(backup_dir)
        self._lock = asyncio.Lock()

        # 确保备份目录存在
        self.backup_dir.mkdir(exist_ok=True)

    def _acquire_file_lock(self, file_obj, non_blocking: bool = False) -> bool:
        """
        获取文件锁

        Args:
            file_obj: 文件对象
            non_blocking: 是否非阻塞模式

        Returns:
            bool: 是否成功获取锁
        """
        try:
            lock_flags = LOCK_EX | (LOCK_NB if non_blocking else 0)
            flock(file_obj.fileno(), lock_flags)
            return True
        except (IOError, OSError) as e:
            # Docker Desktop / 某些挂载文件系统可能不支持 flock，降级为无锁模式
            if getattr(e, "errno", None) in (errno.ENOSYS, errno.EOPNOTSUPP, errno.ENOTSUP):
                print("[ConfigService] File lock not supported, continuing without lock")
                return True
            return False

    def _release_file_lock(self, file_obj):
        """
        释放文件锁

        Args:
            file_obj: 文件对象
        """
        try:
            flock(file_obj.fileno(), LOCK_UN)
        except (IOError, OSError):
            pass  # 锁可能已经释放

    def load_env(self) -> Dict[str, str]:
        """
        读取并解析 .env 文件

        Returns:
            Dict[str, str]: 环境变量字典

        Raises:
            ConfigServiceError: 文件读取失败
        """
        try:
            # 检查文件是否存在
            if not self.env_file.exists():
                print(f"[ConfigService] Env file '{self.env_file}' not found, returning empty dict")
                return {}

            # 使用 dotenv_values 读取，保持注释和格式
            env_values = dotenv_values(str(self.env_file))

            print(f"[ConfigService] Successfully loaded {len(env_values)} variables from '{self.env_file}'")
            return dict(env_values)

        except Exception as e:
            error_msg = f"Failed to load env file '{self.env_file}': {str(e)}"
            print(f"[ConfigService] {error_msg}")
            raise ConfigServiceError(error_msg)

    def create_backup(self) -> str:
        """
        创建 .env 文件备份

        Returns:
            str: 备份文件路径

        Raises:
            ConfigServiceError: 备份创建失败
        """
        try:
            if not self.env_file.exists():
                raise ConfigServiceError(f"Source file '{self.env_file}' does not exist")

            # 生成带时间戳的备份文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{self.env_file.stem}_{timestamp}{self.env_file.suffix}"
            backup_path = self.backup_dir / backup_filename

            # 复制文件
            shutil.copy2(self.env_file, backup_path)

            print(f"[ConfigService] Created backup: '{backup_path}'")
            return str(backup_path)

        except Exception as e:
            error_msg = f"Failed to create backup: {str(e)}"
            print(f"[ConfigService] {error_msg}")
            raise ConfigServiceError(error_msg)

    def restore_backup(self, backup_path: str) -> bool:
        """
        从备份恢复文件

        Args:
            backup_path: 备份文件路径

        Returns:
            bool: 恢复是否成功
        """
        try:
            backup_file = Path(backup_path)

            if not backup_file.exists():
                raise ConfigServiceError(f"Backup file '{backup_path}' does not exist")

            # 创建当前文件的备份
            current_backup = self.create_backup()

            # 从备份恢复
            shutil.copy2(backup_file, self.env_file)

            print(f"[ConfigService] Restored from backup '{backup_path}' (current backup saved to '{current_backup}')")
            return True

        except Exception as e:
            error_msg = f"Failed to restore backup: {str(e)}"
            print(f"[ConfigService] {error_msg}")
            return False


    async def update_env(self, config: Dict[str, str], create_backup: bool = True) -> bool:
        """
        原子性更新 .env 文件

        Args:
            config: 要更新的配置字典
            create_backup: 是否创建备份

        Returns:
            bool: 更新是否成功

        Raises:
            ConfigServiceError: 更新失败
        """
        if not config:
            print("[ConfigService] No config updates provided")
            return True

        async with self._lock:
            try:
                if self.env_file.exists() and self.env_file.is_dir():
                    raise ConfigServiceError(
                        f"Env path '{self.env_file}' is a directory, expected a file. "
                        "Check your bind-mount (e.g. './.env:/app/.env')."
                    )

                # Ensure parent directory exists (for custom env_file paths)
                self.env_file.parent.mkdir(parents=True, exist_ok=True)

                # 创建备份
                if create_backup and self.env_file.exists():
                    try:
                        self.create_backup()
                    except ConfigServiceError as e:
                        # 备份失败不应阻断配置写入（Docker bind-mount 权限/只读目录等场景）
                        print(f"[ConfigService] Backup skipped: {e}")

                # 使用临时文件进行原子写入
                temp_fd, temp_path = tempfile.mkstemp(
                    suffix=self.env_file.suffix,
                    prefix=f"{self.env_file.stem}_tmp_",
                    dir=self.env_file.parent
                )

                try:
                    # 获取文件锁
                    with os.fdopen(temp_fd, 'w', encoding='utf-8') as temp_file:
                        if not self._acquire_file_lock(temp_file):
                            raise ConfigServiceError("Failed to acquire file lock")

                        try:
                            # 如果原文件存在，复制内容和格式
                            if self.env_file.exists():
                                with open(self.env_file, 'r', encoding='utf-8') as original_file:
                                    # 获取原文件的锁
                                    if not self._acquire_file_lock(original_file, non_blocking=True):
                                        raise ConfigServiceError("Original file is locked by another process")

                                    try:
                                        # 读取原文件内容，保留注释和空行
                                        lines = original_file.readlines()
                                        processed_keys = set()

                                        # 处理现有行
                                        for line in lines:
                                            line = line.rstrip()

                                            # 跳过空行和注释
                                            if not line or line.strip().startswith('#'):
                                                temp_file.write(line + '\n')
                                                continue

                                            # 处理配置行
                                            if '=' in line:
                                                key = line.split('=', 1)[0].strip()
                                                if key in config:
                                                    # 更新值
                                                    value = config[key]
                                                    # 处理值的引号和特殊字符
                                                    if any(c in value for c in [' ', '#', '"', "'", '$', '\\']):
                                                        if "'" not in value:
                                                            value = f"'{value}'"
                                                        elif '"' not in value:
                                                            value = f'"{value}"'
                                                        else:
                                                            # 转义已有引号
                                                            value = value.replace('"', '\\"')
                                                            value = f'"{value}"'

                                                    temp_file.write(f"{key}={value}\n")
                                                    processed_keys.add(key)
                                                else:
                                                    # 保持原样
                                                    temp_file.write(line + '\n')
                                            else:
                                                # 保持非配置行原样
                                                temp_file.write(line + '\n')

                                        # 添加新的配置项
                                        for key, value in config.items():
                                            if key not in processed_keys:
                                                # 处理值的引号和特殊字符
                                                if any(c in value for c in [' ', '#', '"', "'", '$', '\\']):
                                                    if "'" not in value:
                                                        value = f"'{value}'"
                                                    elif '"' not in value:
                                                        value = f'"{value}"'
                                                    else:
                                                        # 转义已有引号
                                                        value = value.replace('"', '\\"')
                                                        value = f'"{value}"'

                                                temp_file.write(f"{key}={value}\n")

                                        self._release_file_lock(original_file)

                                    except Exception:
                                        self._release_file_lock(original_file)
                                        raise
                            else:
                                # 文件不存在，创建新文件
                                for key, value in config.items():
                                    # 处理值的引号和特殊字符
                                    if any(c in value for c in [' ', '#', '"', "'", '$', '\\']):
                                        if "'" not in value:
                                            value = f"'{value}'"
                                        elif '"' not in value:
                                            value = f'"{value}"'
                                        else:
                                            # 转义已有引号
                                            value = value.replace('"', '\\"')
                                            value = f'"{value}"'

                                    temp_file.write(f"{key}={value}\n")

                            # 确保数据写入磁盘
                            temp_file.flush()
                            os.fsync(temp_file.fileno())

                            # 原子性替换文件
                            temp_file_path = Path(temp_path)
                            try:
                                temp_file_path.replace(self.env_file)
                            except OSError as e:
                                # 例如将单文件 bind-mount 到容器时，rename/replace 可能出现 EXDEV/EBUSY/EPERM/EACCES
                                if e.errno not in (errno.EXDEV, errno.EBUSY, errno.EPERM, errno.EACCES):
                                    raise

                                print(
                                    "[ConfigService] Atomic replace failed, falling back to direct write "
                                    f"(errno={getattr(e, 'errno', None)}): {e}"
                                )

                                # 回退方案：直接覆盖写入目标文件（非原子，但能兼容跨挂载场景）
                                self.env_file.parent.mkdir(parents=True, exist_ok=True)

                                with open(temp_file_path, 'r', encoding='utf-8') as src_file:
                                    new_content = src_file.read()

                                with open(self.env_file, 'w', encoding='utf-8') as dst_file:
                                    if not self._acquire_file_lock(dst_file):
                                        raise ConfigServiceError("Failed to acquire file lock")
                                    try:
                                        dst_file.write(new_content)
                                        dst_file.flush()
                                        os.fsync(dst_file.fileno())
                                    finally:
                                        self._release_file_lock(dst_file)

                                try:
                                    os.unlink(temp_path)
                                except OSError:
                                    pass

                            print(f"[ConfigService] Successfully updated {len(config)} variables in '{self.env_file}'")
                            return True

                        finally:
                            self._release_file_lock(temp_file)

                except Exception as e:
                    # 清理临时文件
                    try:
                        os.unlink(temp_path)
                    except OSError:
                        pass
                    raise e

            except Exception as e:
                error_msg = f"Failed to update env file: {str(e)}"
                print(f"[ConfigService] {error_msg}")
                raise ConfigServiceError(error_msg)

    def get_backup_list(self) -> list:
        """
        获取备份文件列表

        Returns:
            list: 备份文件信息列表
        """
        backups = []

        try:
            for backup_file in self.backup_dir.glob(f"{self.env_file.stem}_*{self.env_file.suffix}"):
                try:
                    stat = backup_file.stat()
                    backups.append({
                        "filename": backup_file.name,
                        "path": str(backup_file),
                        "size": stat.st_size,
                        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
                except Exception:
                    continue

            # 按创建时间倒序排列
            backups.sort(key=lambda x: x["created"], reverse=True)

        except Exception as e:
            print(f"[ConfigService] Failed to list backups: {str(e)}")

        return backups

    def cleanup_old_backups(self, keep_count: int = 10) -> int:
        """
        清理旧备份文件

        Args:
            keep_count: 保留的备份文件数量

        Returns:
            int: 删除的备份文件数量
        """
        deleted_count = 0

        try:
            backups = self.get_backup_list()

            # 删除超过保留数量的旧备份
            for backup in backups[keep_count:]:
                try:
                    os.remove(backup["path"])
                    deleted_count += 1
                    print(f"[ConfigService] Deleted old backup: {backup['filename']}")
                except Exception as e:
                    print(f"[ConfigService] Failed to delete backup {backup['filename']}: {str(e)}")

        except Exception as e:
            print(f"[ConfigService] Failed to cleanup backups: {str(e)}")

        return deleted_count


# 全局配置服务实例
config_service = ConfigService("env/.env", "env/backups")


def load_env_config() -> Dict[str, str]:
    """
    便捷函数：加载环境配置

    Returns:
        Dict[str, str]: 环境变量字典
    """
    return config_service.load_env()


async def update_env_config(config: Dict[str, str], create_backup: bool = True) -> bool:
    """
    便捷函数：更新环境配置

    Args:
        config: 要更新的配置字典
        create_backup: 是否创建备份

    Returns:
        bool: 更新是否成功
    """
    return await config_service.update_env(config, create_backup)
