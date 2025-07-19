from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from .config import settings

# 同步数据库引擎
if "sqlite" in settings.database_url:
    # SQLite特殊配置，增加超时和WAL模式
    engine = create_engine(
        settings.database_url,
        connect_args={
            "check_same_thread": False,
            "timeout": 30,  # 30秒超时
            "isolation_level": None,  # 关闭事务隔离，使用autocommit
        },
        pool_pre_ping=True,  # 连接池预检查
        pool_recycle=3600,   # 1小时回收连接
        echo=False
    )
else:
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 异步数据库引擎
if "sqlite" in settings.database_url:
    async_database_url = settings.database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
else:
    async_database_url = settings.database_url

async_engine = create_async_engine(
    async_database_url,
    echo=True,
    connect_args={"check_same_thread": False} if "sqlite" in async_database_url else {}
)
AsyncSessionLocal = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

# 基础模型类
Base = declarative_base()

# 数据库依赖
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 异步数据库依赖
async def get_async_db():
    async with AsyncSessionLocal() as session:
        yield session