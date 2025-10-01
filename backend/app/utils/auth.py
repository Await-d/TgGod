from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from ..config import settings
from ..database import get_db
from ..models.user import User

# 密码加密上下文
# 使用bcrypt 4.0.1以确保与passlib 1.7.4的兼容性
# 避免bcrypt 4.2+版本中移除__about__模块导致的警告
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

MAX_PASSWORD_BYTES = 72
PASSWORD_TOO_LONG_MESSAGE = f"密码长度不能超过{MAX_PASSWORD_BYTES}字节（按UTF-8计算），请缩短后重试"


class PasswordTooLongError(ValueError):
    """密码长度超出 bcrypt 支持范围"""

    def __init__(self, message: str = PASSWORD_TOO_LONG_MESSAGE) -> None:
        super().__init__(message)


def ensure_password_length(password: str) -> None:
    """校验密码字节长度，确保符合 bcrypt 限制"""
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise PasswordTooLongError()


# JWT Bearer token认证
security = HTTPBearer()

# JWT配置
SECRET_KEY = settings.jwt_secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60  # 30天


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    try:
        ensure_password_length(plain_password)
        return pwd_context.verify(plain_password, hashed_password)
    except PasswordTooLongError:
        # 密码长度超限，直接抛出
        raise
    except Exception:
        # 其他错误（如哈希格式无效）返回False，而不是误报为密码长度错误
        return False


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    try:
        ensure_password_length(password)
        return pwd_context.hash(password)
    except PasswordTooLongError:
        # 密码长度超限，直接抛出
        raise
    except Exception as exc:
        # 其他异常直接抛出，不转换为密码长度错误
        raise RuntimeError(f"密码哈希生成失败: {exc}") from exc


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建JWT访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """验证JWT令牌"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def get_user(db: Session, username: str) -> Optional[User]:
    """根据用户名获取用户"""
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """根据邮箱获取用户"""
    return db.query(User).filter(User.email == email).first()


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """验证用户身份"""
    user = get_user(db, username)
    if not user:
        return None
    try:
        if not verify_password(password, user.hashed_password):
            return None
    except PasswordTooLongError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        ) from exc
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """获取当前用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = verify_token(credentials.credentials)
        if payload is None:
            raise credentials_exception
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = get_user(db, username=username)
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_superuser(current_user: User = Depends(get_current_user)) -> User:
    """获取当前超级用户"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=400,
            detail="The user doesn't have enough privileges"
        )
    return current_user
