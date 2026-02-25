"""SQLAlchemy 数据库引擎与 Session 工厂。"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)

WORKSPACE = Path(__file__).resolve().parent.parent.parent.parent / "workspace"
DB_PATH = WORKSPACE / "theia.db"

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    echo=False,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Session:
    return SessionLocal()


_NEW_COLUMNS = [
    ("tasks", "thumbnail_path", "TEXT"),
]


def _migrate_add_columns() -> None:
    """Safely add new columns to existing tables (SQLite ALTER TABLE)."""
    with engine.connect() as conn:
        for table, col, col_type in _NEW_COLUMNS:
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                conn.commit()
                logger.info("已添加列 %s.%s", table, col)
            except Exception:
                pass


def init_db() -> None:
    """创建所有表并初始化默认数据。"""
    from .db_models import Base, User

    WORKSPACE.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    logger.info("数据库已初始化: %s", DB_PATH)

    _migrate_add_columns()

    with get_session() as session:
        default = session.query(User).filter_by(id="default").first()
        if not default:
            session.add(User(id="default", name="默认用户"))
            session.commit()
            logger.info("已创建默认用户")
