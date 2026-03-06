from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core import config as config_module
from app.db import session as session_module


@pytest.fixture()
def test_db(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    uploads = data_dir / "uploads"
    extracted = data_dir / "extracted"
    uploads.mkdir(parents=True)
    extracted.mkdir(parents=True)

    monkeypatch.setenv("CHART_DIGEST_DATABASE_URL", f"sqlite:///{(data_dir / 'test.db').as_posix()}")
    monkeypatch.setenv("CHART_DIGEST_UPLOADS_DIR", uploads.as_posix())
    monkeypatch.setenv("CHART_DIGEST_EXTRACTED_DIR", extracted.as_posix())
    config_module.get_settings.cache_clear()
    session_module.settings = config_module.get_settings()
    session_module.engine = create_engine(session_module.settings.database_url, connect_args={"check_same_thread": False})
    session_module.SessionLocal = sessionmaker(
        bind=session_module.engine, autoflush=False, autocommit=False, expire_on_commit=False
    )

    alembic_cfg = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", session_module.settings.database_url)
    alembic_cfg.set_main_option("script_location", str(Path(__file__).resolve().parents[2] / "alembic"))
    command.upgrade(alembic_cfg, "head")

    db = session_module.SessionLocal()
    try:
        yield db
    finally:
        db.close()
        config_module.get_settings.cache_clear()


@pytest.fixture()
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
