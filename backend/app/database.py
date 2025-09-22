"""TgGod数据库配置模块

该模块负责配置和管理SQLAlchemy数据库连接，包括:

- 同步和异步数据库引擎的创建
- 数据库连接池的优化配置
- SQLite和PostgreSQL等不同数据库的适配
- 数据库会话的生命周期管理
- FastAPI依赖注入函数

Features:
    - SQLite特定优化: 超时配置、并发处理、连接回收
    - 连接池预检查和自动重连
    - 异步操作支持
    - 事务管理和会话隔离

Author: TgGod Team
Version: 1.0.0
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
import os

# 基础模型类先创建，避免循环导入
Base = declarative_base()

# 直接使用环境变量获取数据库URL，避免循环导入
database_url = os.environ.get("DATABASE_URL", "sqlite:///./data/tggod.db")

# 动态调整连接池参数
def get_optimal_pool_config():
    """根据系统资源动态计算最优连接池配置"""
    try:
        import psutil
        import os

        # 获取系统资源信息
        cpu_count = os.cpu_count() or 4
        memory_gb = psutil.virtual_memory().total / (1024**3)

        # 基于系统资源计算连接池大小
        # 对于SQLite，连接池不宜过大
        if "sqlite" in database_url:
            base_pool_size = min(max(cpu_count, 5), 15)  # 5-15之间
            max_overflow = min(base_pool_size * 2, 30)   # 最大30个溢出连接
        else:
            # PostgreSQL等其他数据库可以支持更大的连接池
            base_pool_size = min(cpu_count * 2, 20)
            max_overflow = min(base_pool_size * 3, 50)

        return base_pool_size, max_overflow
    except:
        # 回退到默认配置
        return (10, 20) if "sqlite" in database_url else (20, 40)

pool_size, max_overflow = get_optimal_pool_config()

# 同步数据库引擎
if "sqlite" in database_url:
    # SQLite特殊配置，优化并发处理和锁超时
    engine = create_engine(
        database_url,
        connect_args={
            "check_same_thread": False,
            "timeout": 60,  # 增加超时时间，配合WAL模式
            "isolation_level": None,  # 关闭事务隔离，使用autocommit
        },
        pool_pre_ping=True,       # 连接池预检查
        pool_recycle=1800,        # 30分钟回收连接
        pool_size=pool_size,      # 动态计算的连接池大小
        max_overflow=max_overflow, # 动态计算的溢出连接数
        pool_timeout=30,          # 获取连接的超时时间
        pool_reset_on_return='commit',  # 连接返回时自动commit
        echo=False,
        # 连接池事件监听
        pool_logging_name="tggod_pool"
    )
else:
    # PostgreSQL等其他数据库配置
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=3600,        # 1小时回收连接
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=30,
        pool_reset_on_return='commit',
        echo=False,
        pool_logging_name="tggod_pool"
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 异步数据库引擎
if "sqlite" in database_url:
    async_database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
else:
    async_database_url = database_url

async_engine = create_async_engine(
    async_database_url,
    echo=True,
    connect_args={"check_same_thread": False} if "sqlite" in async_database_url else {}
)
AsyncSessionLocal = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

# Base已在文件顶部定义

# 数据库依赖
def get_db():
    """获取同步数据库会话依赖

    FastAPI依赖注入函数，用于在API路由中获取数据库会话。
    自动管理会话的创建和清理，确保资源的正确释放。

    Yields:
        Session: SQLAlchemy数据库会话对象

    Example:
        ```python
        @app.get("/items/")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
        ```

    Note:
        使用try-finally确保会话在请求结束后被正确关闭
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 异步数据库依赖
async def get_async_db():
    """获取异步数据库会话依赖

    FastAPI异步依赖注入函数，用于在异步API路由中获取
    异步数据库会话。适用于需要高并发处理的操作。

    Yields:
        AsyncSession: SQLAlchemy异步数据库会话对象

    Example:
        ```python
        @app.get("/async-items/")
        async def read_async_items(db: AsyncSession = Depends(get_async_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
        ```

    Note:
        - 使用async with语句确保会话的正确管理
        - 适用于长时间运行的数据库操作
        - 支持并发数据库访问和事务管理
    """
    async with AsyncSessionLocal() as session:
        yield session