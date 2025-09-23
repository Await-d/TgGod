"""
Redis会话存储系统
提供分布式会话管理、加密存储和过期机制
"""

import json
import asyncio
import logging
from typing import Dict, Any, Optional, Union
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import hashlib
import base64

import redis.asyncio as redis
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from ..core.exceptions import SessionStoreError
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class RedisSessionStore:
    """Redis会话存储类，支持加密、分布式锁和过期机制"""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        password: Optional[str] = None,
        session_prefix: str = "tggod:session:",
        lock_prefix: str = "tggod:lock:",
        default_ttl: int = 3600,  # 1小时默认过期时间
        encryption_key: Optional[str] = None
    ):
        self.redis_url = redis_url
        self.password = password
        self.session_prefix = session_prefix
        self.lock_prefix = lock_prefix
        self.default_ttl = default_ttl

        # 初始化加密
        if encryption_key:
            self._setup_encryption(encryption_key)
        else:
            self.cipher = None

        self._redis_client: Optional[redis.Redis] = None
        self._connection_pool: Optional[redis.ConnectionPool] = None

    def _setup_encryption(self, password: str):
        """设置数据加密"""
        try:
            # 使用密码生成密钥
            salt = b'tggod_session_salt'  # 生产环境应使用随机salt
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            self.cipher = Fernet(key)
            logger.info("会话加密已启用")
        except Exception as e:
            logger.error(f"设置加密失败: {e}")
            self.cipher = None

    async def initialize(self):
        """初始化Redis连接"""
        try:
            # 创建连接池
            self._connection_pool = redis.ConnectionPool.from_url(
                self.redis_url,
                password=self.password,
                decode_responses=False,  # 保持bytes以支持加密
                max_connections=20,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={
                    1: 1,  # TCP_KEEPIDLE
                    2: 3,  # TCP_KEEPINTVL
                    3: 5,  # TCP_KEEPCNT
                }
            )

            # 创建Redis客户端
            self._redis_client = redis.Redis(connection_pool=self._connection_pool)

            # 测试连接
            await self._redis_client.ping()
            logger.info("Redis会话存储初始化成功")

        except Exception as e:
            logger.error(f"Redis初始化失败: {e}")
            raise SessionStoreError(f"无法连接到Redis: {e}")

    async def close(self):
        """关闭Redis连接"""
        if self._redis_client:
            await self._redis_client.close()
        if self._connection_pool:
            await self._connection_pool.disconnect()
        logger.info("Redis连接已关闭")

    def _encrypt_data(self, data: str) -> bytes:
        """加密数据"""
        if self.cipher:
            return self.cipher.encrypt(data.encode('utf-8'))
        return data.encode('utf-8')

    def _decrypt_data(self, encrypted_data: bytes) -> str:
        """解密数据"""
        if self.cipher:
            return self.cipher.decrypt(encrypted_data).decode('utf-8')
        return encrypted_data.decode('utf-8')

    def _get_session_key(self, session_id: str) -> str:
        """获取会话键名"""
        return f"{self.session_prefix}{session_id}"

    def _get_lock_key(self, session_id: str) -> str:
        """获取锁键名"""
        return f"{self.lock_prefix}{session_id}"

    @asynccontextmanager
    async def session_lock(self, session_id: str, timeout: int = 10):
        """分布式会话锁"""
        lock_key = self._get_lock_key(session_id)
        lock_value = hashlib.md5(f"{session_id}_{datetime.now().isoformat()}".encode()).hexdigest()
        acquired = False

        try:
            # 尝试获取锁
            for _ in range(timeout * 10):  # 每100ms重试一次
                acquired = await self._redis_client.set(
                    lock_key, lock_value, nx=True, ex=timeout
                )
                if acquired:
                    break
                await asyncio.sleep(0.1)

            if not acquired:
                raise SessionStoreError(f"无法获取会话锁: {session_id}")

            logger.debug(f"获取会话锁成功: {session_id}")
            yield

        finally:
            if acquired:
                # 使用Lua脚本安全释放锁
                lua_script = """
                if redis.call("get", KEYS[1]) == ARGV[1] then
                    return redis.call("del", KEYS[1])
                else
                    return 0
                end
                """
                await self._redis_client.eval(lua_script, 1, lock_key, lock_value)
                logger.debug(f"释放会话锁: {session_id}")

    async def set_session(
        self,
        session_id: str,
        data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """设置会话数据"""
        if not self._redis_client:
            raise SessionStoreError("Redis客户端未初始化")

        async with self.session_lock(session_id):
            try:
                key = self._get_session_key(session_id)
                ttl = ttl or self.default_ttl

                # 添加元数据
                session_data = {
                    "data": data,
                    "created_at": datetime.now().isoformat(),
                    "last_access": datetime.now().isoformat(),
                    "ttl": ttl
                }

                # 序列化和加密
                json_data = json.dumps(session_data, ensure_ascii=False)
                encrypted_data = self._encrypt_data(json_data)

                # 存储到Redis
                result = await self._redis_client.set(key, encrypted_data, ex=ttl)

                if result:
                    logger.debug(f"会话数据已保存: {session_id}, TTL: {ttl}秒")
                    return True
                else:
                    logger.error(f"保存会话数据失败: {session_id}")
                    return False

            except Exception as e:
                logger.error(f"设置会话数据异常 {session_id}: {e}")
                raise SessionStoreError(f"设置会话失败: {e}")

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话数据"""
        if not self._redis_client:
            raise SessionStoreError("Redis客户端未初始化")

        try:
            key = self._get_session_key(session_id)
            encrypted_data = await self._redis_client.get(key)

            if not encrypted_data:
                logger.debug(f"会话不存在或已过期: {session_id}")
                return None

            # 解密和反序列化
            json_data = self._decrypt_data(encrypted_data)
            session_data = json.loads(json_data)

            # 更新最后访问时间
            session_data["last_access"] = datetime.now().isoformat()

            # 重新保存以更新访问时间
            updated_json = json.dumps(session_data, ensure_ascii=False)
            updated_encrypted = self._encrypt_data(updated_json)

            # 保持原TTL
            ttl = await self._redis_client.ttl(key)
            if ttl > 0:
                await self._redis_client.set(key, updated_encrypted, ex=ttl)

            logger.debug(f"获取会话数据成功: {session_id}")
            return session_data["data"]

        except json.JSONDecodeError as e:
            logger.error(f"会话数据解析失败 {session_id}: {e}")
            await self.delete_session(session_id)  # 清理损坏的数据
            return None
        except Exception as e:
            logger.error(f"获取会话数据异常 {session_id}: {e}")
            raise SessionStoreError(f"获取会话失败: {e}")

    async def delete_session(self, session_id: str) -> bool:
        """删除会话数据"""
        if not self._redis_client:
            raise SessionStoreError("Redis客户端未初始化")

        try:
            key = self._get_session_key(session_id)
            result = await self._redis_client.delete(key)

            if result:
                logger.debug(f"会话已删除: {session_id}")
                return True
            else:
                logger.debug(f"会话不存在: {session_id}")
                return False

        except Exception as e:
            logger.error(f"删除会话异常 {session_id}: {e}")
            raise SessionStoreError(f"删除会话失败: {e}")

    async def exists_session(self, session_id: str) -> bool:
        """检查会话是否存在"""
        if not self._redis_client:
            raise SessionStoreError("Redis客户端未初始化")

        try:
            key = self._get_session_key(session_id)
            result = await self._redis_client.exists(key)
            return bool(result)
        except Exception as e:
            logger.error(f"检查会话存在性异常 {session_id}: {e}")
            return False

    async def extend_session(self, session_id: str, additional_ttl: int) -> bool:
        """延长会话过期时间"""
        if not self._redis_client:
            raise SessionStoreError("Redis客户端未初始化")

        try:
            key = self._get_session_key(session_id)
            current_ttl = await self._redis_client.ttl(key)

            if current_ttl > 0:
                new_ttl = current_ttl + additional_ttl
                result = await self._redis_client.expire(key, new_ttl)

                if result:
                    logger.debug(f"会话TTL已延长: {session_id}, 新TTL: {new_ttl}秒")
                    return True

            return False

        except Exception as e:
            logger.error(f"延长会话TTL异常 {session_id}: {e}")
            return False

    async def list_sessions(self, pattern: str = "*") -> list[str]:
        """列出匹配的会话ID"""
        if not self._redis_client:
            raise SessionStoreError("Redis客户端未初始化")

        try:
            search_pattern = f"{self.session_prefix}{pattern}"
            keys = await self._redis_client.keys(search_pattern)

            # 提取session_id
            session_ids = []
            for key in keys:
                key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                if key_str.startswith(self.session_prefix):
                    session_id = key_str[len(self.session_prefix):]
                    session_ids.append(session_id)

            return session_ids

        except Exception as e:
            logger.error(f"列出会话异常: {e}")
            return []

    async def clear_expired_sessions(self) -> int:
        """清理已过期的会话（Redis会自动删除，此方法用于统计）"""
        if not self._redis_client:
            raise SessionStoreError("Redis客户端未初始化")

        try:
            # Redis会自动清理过期键，这里只是获取当前活跃会话数
            all_sessions = await self.list_sessions()
            logger.info(f"当前活跃会话数: {len(all_sessions)}")
            return len(all_sessions)

        except Exception as e:
            logger.error(f"清理过期会话异常: {e}")
            return 0

    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话元信息"""
        if not self._redis_client:
            raise SessionStoreError("Redis客户端未初始化")

        try:
            key = self._get_session_key(session_id)

            # 获取TTL
            ttl = await self._redis_client.ttl(key)
            if ttl <= 0:
                return None

            # 获取完整会话数据
            encrypted_data = await self._redis_client.get(key)
            if not encrypted_data:
                return None

            json_data = self._decrypt_data(encrypted_data)
            session_data = json.loads(json_data)

            return {
                "session_id": session_id,
                "ttl": ttl,
                "created_at": session_data.get("created_at"),
                "last_access": session_data.get("last_access"),
                "data_size": len(json_data)
            }

        except Exception as e:
            logger.error(f"获取会话信息异常 {session_id}: {e}")
            return None


# 全局会话存储实例
_session_store: Optional[RedisSessionStore] = None


async def get_session_store() -> RedisSessionStore:
    """获取全局会话存储实例"""
    global _session_store

    if _session_store is None:
        from ..config import settings

        # 从配置获取Redis设置
        redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
        redis_password = getattr(settings, 'REDIS_PASSWORD', None)
        encryption_key = getattr(settings, 'SESSION_ENCRYPTION_KEY', None) or getattr(settings, 'SECRET_KEY', None)

        _session_store = RedisSessionStore(
            redis_url=redis_url,
            password=redis_password,
            encryption_key=encryption_key
        )

        await _session_store.initialize()
        logger.info("全局Redis会话存储已初始化")

    return _session_store


async def close_session_store():
    """关闭全局会话存储"""
    global _session_store

    if _session_store:
        await _session_store.close()
        _session_store = None
        logger.info("全局Redis会话存储已关闭")


# 便捷函数
async def set_auth_session(session_id: str, auth_data: Dict[str, Any], ttl: int = 3600) -> bool:
    """设置认证会话"""
    store = await get_session_store()
    return await store.set_session(session_id, auth_data, ttl)


async def get_auth_session(session_id: str) -> Optional[Dict[str, Any]]:
    """获取认证会话"""
    store = await get_session_store()
    return await store.get_session(session_id)


async def delete_auth_session(session_id: str) -> bool:
    """删除认证会话"""
    store = await get_session_store()
    return await store.delete_session(session_id)


async def extend_auth_session(session_id: str, additional_ttl: int = 1800) -> bool:
    """延长认证会话"""
    store = await get_session_store()
    return await store.extend_session(session_id, additional_ttl)