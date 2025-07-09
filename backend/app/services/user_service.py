import logging
from sqlalchemy.orm import Session
from ..models.user import User
from ..utils.auth import get_password_hash, get_user, get_user_by_email
from ..config import settings

logger = logging.getLogger(__name__)


class UserService:
    """用户服务"""

    @staticmethod
    def create_default_admin(db: Session) -> User:
        """创建默认管理员账户"""
        try:
            # 检查是否已存在管理员账户
            existing_admin = db.query(User).filter(
                User.is_superuser == True
            ).first()
            
            if existing_admin:
                logger.info(f"管理员账户已存在: {existing_admin.username}")
                return existing_admin
            
            # 检查默认用户名和邮箱是否被占用
            username = settings.default_admin_username
            email = settings.default_admin_email
            password = settings.default_admin_password
            
            # 验证配置是否有效
            if not username or not email or not password:
                raise ValueError("默认管理员账户配置不完整")
                
            existing_user = get_user(db, username)
            if existing_user:
                if existing_user.is_superuser:
                    logger.info(f"现有用户 '{username}' 已是管理员")
                    return existing_user
                else:
                    # 将现有用户升级为管理员
                    existing_user.is_superuser = True
                    existing_user.is_verified = True
                    db.commit()
                    db.refresh(existing_user)
                    logger.info(f"用户 '{username}' 已升级为管理员")
                    return existing_user
            
            existing_email = get_user_by_email(db, email)
            if existing_email:
                if existing_email.is_superuser:
                    logger.info(f"现有邮箱 '{email}' 用户已是管理员")
                    return existing_email
                else:
                    # 将现有用户升级为管理员
                    existing_email.is_superuser = True
                    existing_email.is_verified = True
                    db.commit()
                    db.refresh(existing_email)
                    logger.info(f"邮箱 '{email}' 用户已升级为管理员")
                    return existing_email
            
            # 创建默认管理员账户
            hashed_password = get_password_hash(password)
            admin_user = User(
                username=username,
                email=email,
                hashed_password=hashed_password,
                full_name="系统管理员",
                is_active=True,
                is_superuser=True,
                is_verified=True
            )
            
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            
            logger.info(f"默认管理员账户创建成功: {username}")
            return admin_user
            
        except Exception as e:
            logger.error(f"创建默认管理员账户失败: {e}")
            db.rollback()
            raise e

    @staticmethod
    def ensure_default_accounts(db: Session) -> dict:
        """确保默认账户存在"""
        try:
            # 创建默认管理员账户
            admin_user = UserService.create_default_admin(db)
            
            # 可以在这里添加其他默认账户的创建逻辑
            # 例如：创建测试账户、演示账户等
            
            result = {
                "success": True,
                "admin_user": {
                    "id": admin_user.id,
                    "username": admin_user.username,
                    "email": admin_user.email,
                    "is_superuser": admin_user.is_superuser,
                    "created_at": admin_user.created_at
                },
                "message": "默认账户检查完成"
            }
            
            logger.info("默认账户检查完成")
            return result
            
        except Exception as e:
            logger.error(f"确保默认账户存在时发生错误: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "默认账户检查失败"
            }

    @staticmethod
    def initialize_system(db: Session) -> dict:
        """系统初始化"""
        try:
            logger.info("开始系统初始化...")
            
            # 1. 确保默认账户存在
            accounts_result = UserService.ensure_default_accounts(db)
            
            if not accounts_result["success"]:
                return accounts_result
            
            # 2. 检查系统状态
            total_users = db.query(User).count()
            admin_users = db.query(User).filter(User.is_superuser == True).count()
            
            init_result = {
                "success": True,
                "system_status": {
                    "total_users": total_users,
                    "admin_users": admin_users,
                    "default_admin": accounts_result["admin_user"]
                },
                "message": "系统初始化完成"
            }
            
            logger.info(f"系统初始化完成 - 总用户数: {total_users}, 管理员数: {admin_users}")
            return init_result
            
        except Exception as e:
            logger.error(f"系统初始化失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "系统初始化失败"
            }

    @staticmethod
    def get_admin_info() -> dict:
        """获取管理员账户信息（用于初始化提示）"""
        return {
            "username": settings.default_admin_username,
            "password": settings.default_admin_password,
            "email": settings.default_admin_email,
            "note": "这是系统默认管理员账户，建议首次登录后立即修改密码"
        }


# 创建全局服务实例
user_service = UserService()