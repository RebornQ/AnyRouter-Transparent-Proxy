import asyncio
import errno
import tempfile
import time
from pathlib import Path
from unittest.mock import patch
import pytest

from backend.services.config_service import ConfigService, ConfigServiceError


class TestConfigService:
    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def service(self, temp_dir):
        env_file = temp_dir / ".env"
        backup_dir = temp_dir / "backups"
        return ConfigService(str(env_file), str(backup_dir))

    def test_init_creates_backup_dir(self, temp_dir):
        backup_dir = temp_dir / "backups"
        service = ConfigService(str(temp_dir / ".env"), str(backup_dir))
        assert backup_dir.exists()

    def test_load_env_file_not_exists(self, service):
        result = service.load_env()
        assert result == {}

    def test_load_env_success(self, service):
        service.env_file.write_text("KEY1=value1\nKEY2=value2\n")
        result = service.load_env()
        assert result == {"KEY1": "value1", "KEY2": "value2"}

    def test_load_env_failure(self, service):
        service.env_file.write_text("invalid content")
        with patch('backend.services.config_service.dotenv_values', side_effect=Exception("Parse error")):
            with pytest.raises(ConfigServiceError, match="Failed to load env file"):
                service.load_env()

    def test_create_backup_success(self, service):
        service.env_file.write_text("KEY=value\n")
        backup_path = service.create_backup()
        assert Path(backup_path).exists()
        assert Path(backup_path).read_text() == "KEY=value\n"

    def test_create_backup_source_not_exists(self, service):
        with pytest.raises(ConfigServiceError, match="does not exist"):
            service.create_backup()

    def test_create_backup_failure(self, service):
        service.env_file.write_text("KEY=value\n")
        with patch('shutil.copy2', side_effect=Exception("Copy error")):
            with pytest.raises(ConfigServiceError, match="Failed to create backup"):
                service.create_backup()

    def test_restore_backup_success(self, service):
        service.env_file.write_text("OLD=value\n")
        backup_path = service.create_backup()
        time.sleep(1.1)
        service.env_file.write_text("NEW=value\n")
        result = service.restore_backup(backup_path)
        assert result is True
        assert service.env_file.read_text() == "OLD=value\n"

    def test_restore_backup_not_exists(self, service):
        result = service.restore_backup("nonexistent.env")
        assert result is False

    def test_update_env_empty_config(self, service):
        result = asyncio.run(service.update_env({}))
        assert result is True

    def test_update_env_create_new_file(self, service):
        result = asyncio.run(service.update_env({"KEY1": "value1", "KEY2": "value2"}, create_backup=False))
        assert result is True
        content = service.env_file.read_text()
        assert "KEY1=value1" in content
        assert "KEY2=value2" in content

    def test_update_env_update_existing(self, service):
        service.env_file.write_text("KEY1=old\nKEY2=value2\n")
        result = asyncio.run(service.update_env({"KEY1": "new"}, create_backup=False))
        assert result is True
        content = service.env_file.read_text()
        assert "KEY1=new" in content
        assert "KEY2=value2" in content

    def test_update_env_preserve_comments(self, service):
        service.env_file.write_text("# Comment\nKEY1=old\n\nKEY2=value2\n")
        result = asyncio.run(service.update_env({"KEY1": "new"}, create_backup=False))
        assert result is True
        content = service.env_file.read_text()
        assert "# Comment" in content
        assert "KEY1=new" in content

    def test_update_env_special_characters(self, service):
        result = asyncio.run(service.update_env({"KEY": "value with spaces"}, create_backup=False))
        assert result is True
        content = service.env_file.read_text()
        assert "KEY='value with spaces'" in content

    def test_update_env_with_backup(self, service):
        service.env_file.write_text("KEY=old\n")
        result = asyncio.run(service.update_env({"KEY": "new"}, create_backup=True))
        assert result is True
        backups = list(service.backup_dir.glob(".env_*"))
        assert len(backups) == 1

    def test_update_env_backup_failure_is_non_fatal(self, service):
        service.env_file.write_text("KEY=old\n")
        with patch.object(service, "create_backup", side_effect=ConfigServiceError("backup error")):
            result = asyncio.run(service.update_env({"KEY": "new"}, create_backup=True))
        assert result is True
        assert "KEY=new" in service.env_file.read_text()

    def test_update_env_fallback_on_replace_ebusy(self, service):
        service.env_file.write_text("KEY=old\n")
        with patch("pathlib.Path.replace", side_effect=OSError(errno.EBUSY, "Device or resource busy")):
            result = asyncio.run(service.update_env({"KEY": "new"}, create_backup=False))
        assert result is True
        assert "KEY=new" in service.env_file.read_text()

    def test_update_env_failure(self, service):
        with patch('tempfile.mkstemp', side_effect=Exception("Temp error")):
            with pytest.raises(ConfigServiceError, match="Failed to update env file"):
                asyncio.run(service.update_env({"KEY": "value"}))

    def test_get_backup_list_empty(self, service):
        result = service.get_backup_list()
        assert result == []

    def test_get_backup_list_sorted(self, service):
        service.env_file.write_text("KEY=v1\n")
        service.create_backup()
        time.sleep(1.1)
        service.env_file.write_text("KEY=v2\n")
        service.create_backup()
        backups = service.get_backup_list()
        assert len(backups) == 2
        assert backups[0]["created"] >= backups[1]["created"]

    def test_cleanup_old_backups(self, service):
        service.env_file.write_text("KEY=value\n")
        for i in range(5):
            service.create_backup()
            if i < 4:
                time.sleep(1.1)
        deleted = service.cleanup_old_backups(keep_count=2)
        assert deleted == 3
        remaining = list(service.backup_dir.glob(".env_*"))
        assert len(remaining) == 2

    def test_file_lock_acquire_success(self, service):
        with tempfile.NamedTemporaryFile() as f:
            result = service._acquire_file_lock(f, non_blocking=True)
            assert result is True
            service._release_file_lock(f)

    def test_file_lock_acquire_failure(self, service):
        with tempfile.NamedTemporaryFile() as f:
            with patch('backend.services.config_service.flock', side_effect=IOError("Lock failed")):
                result = service._acquire_file_lock(f, non_blocking=True)
                assert result is False

    def test_multiple_sequential_updates(self, service):
        service.env_file.write_text("KEY=initial\n")
        for i in range(3):
            result = asyncio.run(service.update_env({"KEY": f"value{i}"}, create_backup=False))
            assert result is True
        assert "KEY=value2" in service.env_file.read_text()
