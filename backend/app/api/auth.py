from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, validator
from ..database import get_db
from ..models.user import User
from ..utils.auth import (
    authenticate_user,
    create_access_token,
    get_password_hash,
    get_user,
    get_user_by_email,
    get_current_active_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

router = APIRouter()


# Pydantic模型
class UserCreate(BaseModel):
    """用户创建模型"""
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    
    @validator('username')
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError('用户名长度不能少于3个字符')
        if len(v) > 50:
            raise ValueError('用户名长度不能超过50个字符')
        if not v.isalnum():
            raise ValueError('用户名只能包含字母和数字')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('密码长度不能少于6个字符')
        return v


class UserResponse(BaseModel):
    """用户响应模型"""
    id: int
    username: str
    email: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    bio: Optional[str]
    is_active: bool
    is_superuser: bool
    is_verified: bool
    created_at: datetime
    updated_at: Optional[datetime]
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """用户更新模型"""
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None


class Token(BaseModel):
    """令牌模型"""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """令牌数据模型"""
    username: Optional[str] = None


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """用户注册"""
    # 检查用户名是否已存在
    if get_user(db, user.username):
        raise HTTPException(
            status_code=400,
            detail="用户名已存在"
        )
    
    # 检查邮箱是否已存在
    if get_user_by_email(db, user.email):
        raise HTTPException(
            status_code=400,
            detail="邮箱已存在"
        )
    
    # 创建新用户
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        is_active=True,
        is_superuser=False,
        is_verified=False
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """用户登录"""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户已被禁用",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 更新最后登录时间
    user.last_login = datetime.utcnow()
    db.commit()
    
    # 创建访问令牌
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_active_user)):
    """获取当前用户信息"""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新当前用户信息"""
    # 更新用户信息
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    if user_update.avatar_url is not None:
        current_user.avatar_url = user_update.avatar_url
    if user_update.bio is not None:
        current_user.bio = user_update.bio
    
    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_active_user)):
    """用户登出"""
    # 由于JWT是无状态的，这里只是一个占位符
    # 在实际应用中，可以将token加入黑名单或设置短期过期时间
    return {"message": "登出成功"}


@router.get("/users", response_model=list[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 10,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取用户列表（需要登录）"""
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.get("/admin-info")
async def get_admin_info():
    """获取默认管理员账户信息（仅用于初始化提示）"""
    from ..services.user_service import user_service
    admin_info = user_service.get_admin_info()
    return {
        "message": "默认管理员账户信息",
        "data": admin_info,
        "warning": "首次登录后请立即修改密码！"
    }