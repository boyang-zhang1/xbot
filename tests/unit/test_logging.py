
from xbot.config import settings as settings_module
from xbot.utils.logging import configure_logging


def test_configure_logging_creates_log_file(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    data_dir = tmp_path / "data"

    monkeypatch.setenv("APP_LOG_DIR", str(log_dir))
    monkeypatch.setenv("APP_DATA_DIR", str(data_dir))

    settings_module.get_settings.cache_clear()  # type: ignore[attr-defined]
    logger = configure_logging(settings_module.get_settings())

    assert log_dir.exists()
    log_file = log_dir / "xbot.log"
    assert log_file.exists()
    logger.info("structured message")
