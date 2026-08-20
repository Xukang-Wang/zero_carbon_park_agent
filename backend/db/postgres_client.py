"""
zero_carbon_park_agent 数据库客户端（基于 SQLAlchemy + SQLite）
轻量级替代 PostgreSQL，无需额外安装数据库服务
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATABASE_URL

engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def get_db():
    """获取数据库会话（FastAPI 依赖注入）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库表结构"""
    from db.models import WaterQualityRecord, WaterPredictionResult, AnomalyEvent, WorkflowExecution
    Base.metadata.create_all(bind=engine)
    print("数据库表初始化完成")


def get_session():
    """直接获取数据库会话（非 FastAPI 场景）"""
    return SessionLocal()