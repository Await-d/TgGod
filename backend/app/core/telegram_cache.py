"""
Telegram查询缓存层

提供多级缓存策略，优化数据库查询性能，支持预加载和智能失效机制。

主要功能:
- 多级缓存（内存+Redis）
- 查询结果缓存
- 批量查询优化
- 智能预加载
- 权限感知缓存
- 缓存失效策略

Author: TgGod Team
Version: 1.0.0
"""

import asyncio
import json
import hashlib
import logging
import time
import threading
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """缓存级别"""
    MEMORY = "memory"       # 内存缓存
    REDIS = "redis"         # Redis缓存
    DATABASE = "database"   # 数据库缓存


class CachePolicy(Enum):
    """缓存策略"""
    LRU = "lru"            # 最近最少使用
    LFU = "lfu"            # 最少使用频率
    TTL = "ttl"            # 时间过期
    FIFO = "fifo"          # 先进先出


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: float
    last_access: float
    access_count: int
    ttl: Optional[float]
    size_bytes: int
    tags: Set[str]

    @property
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl

    @property
    def age_seconds(self) -> float:
        """获取缓存年龄（秒）"""
        return time.time() - self.created_at


@dataclass
class QueryContext:
    """查询上下文"""
    user_id: Optional[int]
    permissions: Set[str]
    chat_id: Optional[int]
    query_type: str
    priority: int = 1


class MemoryCache:
    """内存缓存实现"""

    def __init__(self, max_size: int = 1000, max_memory_mb: int = 100,
                 default_ttl: int = 300, policy: CachePolicy = CachePolicy.LRU):
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.default_ttl = default_ttl
        self.policy = policy

        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._tags_index: Dict[str, Set[str]] = defaultdict(set)  # tag -> keys
        self._access_frequency: Dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()

        # 统计信息
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.current_memory_bytes = 0

    def get(self, key: str, default: Any = None) -> Any:
        """获取缓存值"""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self.misses += 1
                return default

            if entry.is_expired:
                self._remove_entry(key)
                self.misses += 1
                return default

            # 更新访问信息
            entry.last_access = time.time()
            entry.access_count += 1
            self._access_frequency[key] += 1

            # LRU策略：移到末尾
            if self.policy == CachePolicy.LRU:
                self._cache.move_to_end(key)

            self.hits += 1
            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[float] = None,
            tags: Optional[Set[str]] = None) -> bool:
        """设置缓存值"""
        with self._lock:
            tags = tags or set()
            size_bytes = self._estimate_size(value)

            # 检查是否需要清理空间
            if not self._ensure_space(size_bytes):
                return False

            # 创建缓存条目
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                last_access=time.time(),
                access_count=0,
                ttl=ttl or self.default_ttl,
                size_bytes=size_bytes,
                tags=tags
            )

            # 如果key已存在，先移除旧条目
            if key in self._cache:
                self._remove_entry(key)

            # 添加新条目
            self._cache[key] = entry
            self.current_memory_bytes += size_bytes

            # 更新标签索引
            for tag in tags:
                self._tags_index[tag].add(key)

            return True

    def delete(self, key: str) -> bool:
        """删除缓存条目"""
        with self._lock:
            if key in self._cache:
                self._remove_entry(key)
                return True
            return False

    def delete_by_tags(self, tags: Set[str]) -> int:
        """根据标签删除缓存条目"""
        with self._lock:
            keys_to_delete = set()
            for tag in tags:
                keys_to_delete.update(self._tags_index.get(tag, set()))

            for key in keys_to_delete:
                self._remove_entry(key)

            return len(keys_to_delete)

    def clear(self) -> int:
        """清空缓存"""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._tags_index.clear()
            self._access_frequency.clear()
            self.current_memory_bytes = 0
            return count

    def _remove_entry(self, key: str):
        """移除缓存条目"""
        entry = self._cache.pop(key, None)
        if entry:
            self.current_memory_bytes -= entry.size_bytes

            # 清理标签索引
            for tag in entry.tags:
                self._tags_index[tag].discard(key)
                if not self._tags_index[tag]:
                    del self._tags_index[tag]

            # 清理访问频率
            self._access_frequency.pop(key, None)

    def _ensure_space(self, required_bytes: int) -> bool:
        """确保有足够空间"""
        # 检查大小限制
        while (len(self._cache) >= self.max_size or
               self.current_memory_bytes + required_bytes > self.max_memory_bytes):

            if not self._cache:
                return False

            # 根据策略选择要淘汰的条目
            key_to_evict = self._select_eviction_key()
            if key_to_evict:
                self._remove_entry(key_to_evict)
                self.evictions += 1
            else:
                return False

        return True

    def _select_eviction_key(self) -> Optional[str]:
        """选择要淘汰的key"""
        if not self._cache:
            return None

        if self.policy == CachePolicy.LRU:
            # 选择最近最少使用的（最前面的）
            return next(iter(self._cache))

        elif self.policy == CachePolicy.LFU:
            # 选择使用频率最低的
            return min(self._cache.keys(),
                      key=lambda k: self._access_frequency.get(k, 0))

        elif self.policy == CachePolicy.TTL:
            # 选择最老的
            return min(self._cache.keys(),
                      key=lambda k: self._cache[k].created_at)

        elif self.policy == CachePolicy.FIFO:
            # 选择最先进入的
            return next(iter(self._cache))

        return next(iter(self._cache))  # 默认

    def _estimate_size(self, value: Any) -> int:
        """估算值的大小"""
        try:
            import sys
            if isinstance(value, (str, bytes)):
                return len(value)
            elif isinstance(value, (list, tuple)):
                return sum(sys.getsizeof(item) for item in value)
            elif isinstance(value, dict):
                return sum(sys.getsizeof(k) + sys.getsizeof(v)
                          for k, v in value.items())
            else:
                return sys.getsizeof(value)
        except:
            return 1024  # 默认1KB

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "total_entries": len(self._cache),
            "max_size": self.max_size,
            "memory_usage_mb": self.current_memory_bytes / (1024 * 1024),
            "max_memory_mb": self.max_memory_bytes / (1024 * 1024),
            "evictions": self.evictions,
            "policy": self.policy.value,
            "tags_count": len(self._tags_index)
        }


class TelegramQueryCache:
    """Telegram查询缓存主类"""

    def __init__(self, memory_cache_size: int = 1000, memory_limit_mb: int = 100,
                 default_ttl: int = 300, enable_redis: bool = False):

        # 内存缓存
        self.memory_cache = MemoryCache(
            max_size=memory_cache_size,
            max_memory_mb=memory_limit_mb,
            default_ttl=default_ttl
        )

        # Redis缓存（可选）
        self.redis_cache = None
        self.enable_redis = enable_redis
        if enable_redis:
            try:
                self._init_redis_cache()
            except Exception as e:
                logger.warning(f"Redis缓存初始化失败: {e}")
                self.enable_redis = False

        # 查询优化配置
        self.batch_query_threshold = 5  # 批量查询阈值
        self.preload_enabled = True
        self.permission_cache_enabled = True

        # 查询统计
        self.query_stats = defaultdict(int)
        self.batch_queries = defaultdict(list)
        self.preload_queue = None

        # 权限缓存
        self.permission_cache = MemoryCache(max_size=500, default_ttl=60)  # 1分钟权限缓存

        # 预加载任务
        self._preload_task = None
        self._preload_enabled = True

    def _init_redis_cache(self):
        """初始化Redis缓存"""
        try:
            import redis
            self.redis_cache = redis.Redis(
                host='localhost',
                port=6379,
                db=1,  # 使用DB1避免冲突
                decode_responses=True
            )
            # 测试连接
            self.redis_cache.ping()
            logger.info("Redis缓存已启用")
        except ImportError:
            logger.warning("Redis库未安装，跳过Redis缓存")
            raise
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            raise

    def _generate_cache_key(self, query_type: str, params: Dict[str, Any],
                           context: Optional[QueryContext] = None) -> str:
        """生成缓存键"""
        # 基础键
        key_parts = [query_type]

        # 添加参数
        if params:
            # 排序参数确保一致性
            sorted_params = sorted(params.items())
            params_str = json.dumps(sorted_params, sort_keys=True, default=str)
            key_parts.append(hashlib.md5(params_str.encode()).hexdigest()[:16])

        # 添加权限上下文
        if context and self.permission_cache_enabled:
            permission_key = hashlib.md5(
                str(sorted(context.permissions)).encode()
            ).hexdigest()[:8]
            key_parts.append(f"perm_{permission_key}")

        return ":".join(key_parts)

    def _generate_cache_tags(self, query_type: str, params: Dict[str, Any],
                           context: Optional[QueryContext] = None) -> Set[str]:
        """生成缓存标签"""
        tags = {f"type_{query_type}"}

        # 添加实体标签
        if 'group_id' in params:
            tags.add(f"group_{params['group_id']}")
        if 'message_id' in params:
            tags.add(f"message_{params['message_id']}")
        if 'user_id' in params:
            tags.add(f"user_{params['user_id']}")

        # 添加权限标签
        if context:
            if context.user_id:
                tags.add(f"user_ctx_{context.user_id}")
            if context.chat_id:
                tags.add(f"chat_{context.chat_id}")

        return tags

    async def get_cached_query(self, query_type: str, params: Dict[str, Any],
                              context: Optional[QueryContext] = None,
                              ttl: Optional[int] = None) -> Optional[Any]:
        """获取缓存的查询结果"""
        cache_key = self._generate_cache_key(query_type, params, context)

        # 首先检查内存缓存
        result = self.memory_cache.get(cache_key)
        if result is not None:
            self.query_stats[f"{query_type}_memory_hit"] += 1
            return result

        # 检查Redis缓存
        if self.enable_redis and self.redis_cache:
            try:
                redis_result = self.redis_cache.get(cache_key)
                if redis_result:
                    # 反序列化并放入内存缓存
                    result = json.loads(redis_result)
                    self.memory_cache.set(cache_key, result, ttl=ttl)
                    self.query_stats[f"{query_type}_redis_hit"] += 1
                    return result
            except Exception as e:
                logger.warning(f"Redis缓存读取失败: {e}")

        self.query_stats[f"{query_type}_miss"] += 1
        return None

    async def set_cached_query(self, query_type: str, params: Dict[str, Any],
                              result: Any, context: Optional[QueryContext] = None,
                              ttl: Optional[int] = None) -> bool:
        """设置查询结果缓存"""
        cache_key = self._generate_cache_key(query_type, params, context)
        cache_tags = self._generate_cache_tags(query_type, params, context)

        # 设置内存缓存
        memory_success = self.memory_cache.set(cache_key, result, ttl=ttl, tags=cache_tags)

        # 设置Redis缓存
        redis_success = True
        if self.enable_redis and self.redis_cache:
            try:
                serialized = json.dumps(result, default=str)
                if ttl:
                    self.redis_cache.setex(cache_key, ttl, serialized)
                else:
                    self.redis_cache.set(cache_key, serialized)
            except Exception as e:
                logger.warning(f"Redis缓存写入失败: {e}")
                redis_success = False

        self.query_stats[f"{query_type}_set"] += 1
        return memory_success and redis_success

    async def invalidate_cache(self, tags: Optional[Set[str]] = None,
                              keys: Optional[List[str]] = None,
                              query_type: Optional[str] = None) -> Dict[str, int]:
        """使缓存失效"""
        result = {"memory": 0, "redis": 0}

        # 内存缓存失效
        if tags:
            result["memory"] = self.memory_cache.delete_by_tags(tags)
        elif keys:
            for key in keys:
                if self.memory_cache.delete(key):
                    result["memory"] += 1
        elif query_type:
            # 根据查询类型失效
            type_tags = {f"type_{query_type}"}
            result["memory"] = self.memory_cache.delete_by_tags(type_tags)

        # Redis缓存失效
        if self.enable_redis and self.redis_cache:
            try:
                if keys:
                    result["redis"] = self.redis_cache.delete(*keys)
                elif query_type:
                    # Redis中需要用模式匹配
                    pattern = f"{query_type}:*"
                    redis_keys = self.redis_cache.keys(pattern)
                    if redis_keys:
                        result["redis"] = self.redis_cache.delete(*redis_keys)
            except Exception as e:
                logger.warning(f"Redis缓存失效失败: {e}")

        return result

    async def check_user_permissions(self, user_id: int, chat_id: int,
                                   required_permissions: Set[str]) -> bool:
        """检查用户权限（带缓存）"""
        if not self.permission_cache_enabled:
            return True  # 禁用权限检查时默认通过

        cache_key = f"perm_{user_id}_{chat_id}"
        cached_permissions = self.permission_cache.get(cache_key)

        if cached_permissions is None:
            # 查询用户权限（需要与权限服务集成）
            cached_permissions = await self._fetch_user_permissions(user_id, chat_id)
            self.permission_cache.set(cache_key, cached_permissions, ttl=60)

        return required_permissions.issubset(set(cached_permissions))

    async def _fetch_user_permissions(self, user_id: int, chat_id: int) -> List[str]:
        """获取用户权限（需要实际实现）"""
        # TODO: 实际的权限查询逻辑
        # 这里返回模拟的权限列表
        return ["read", "write", "admin"] if user_id == 1 else ["read"]

    def get_cache_statistics(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        stats = {
            "memory_cache": self.memory_cache.get_stats(),
            "permission_cache": self.permission_cache.get_stats(),
            "query_stats": dict(self.query_stats),
            "redis_enabled": self.enable_redis,
            "preload_enabled": self.preload_enabled,
            "permission_cache_enabled": self.permission_cache_enabled
        }

        if self.enable_redis and self.redis_cache:
            try:
                redis_info = self.redis_cache.info('memory')
                stats["redis_stats"] = {
                    "used_memory": redis_info.get('used_memory'),
                    "used_memory_human": redis_info.get('used_memory_human'),
                    "connected_clients": self.redis_cache.info('clients').get('connected_clients')
                }
            except Exception as e:
                stats["redis_error"] = str(e)

        return stats


# 全局缓存实例
telegram_cache = TelegramQueryCache()


def get_telegram_cache() -> TelegramQueryCache:
    """获取Telegram缓存实例"""
    return telegram_cache


async def cached_query(query_type: str, params: Dict[str, Any],
                      context: Optional[QueryContext] = None,
                      ttl: Optional[int] = None):
    """缓存查询装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 检查缓存
            cached_result = await telegram_cache.get_cached_query(
                query_type, params, context, ttl
            )
            if cached_result is not None:
                return cached_result

            # 执行实际查询
            result = await func(*args, **kwargs)

            # 缓存结果
            await telegram_cache.set_cached_query(
                query_type, params, result, context, ttl
            )

            return result
        return wrapper
    return decorator


def with_permission_check(required_permissions: Set[str]):
    """权限检查装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            context = kwargs.get('context')
            if context and isinstance(context, QueryContext):
                # 检查权限
                has_permission = await telegram_cache.check_user_permissions(
                    context.user_id, context.chat_id or 0, required_permissions
                )
                if not has_permission:
                    raise PermissionError(f"缺少必要权限: {required_permissions}")

            return await func(*args, **kwargs)
        return wrapper
    return decorator