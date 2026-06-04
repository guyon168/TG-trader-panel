"""网络请求重试工具

提供带指数退避的重试装饰器，用于交易所 API 和 Telegram API 调用。
"""
import asyncio
import functools
import logging
from typing import Type, Tuple, Optional

logger = logging.getLogger(__name__)

# 默认需要重试的异常类型
DEFAULT_RETRY_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    OSError,
)

# ImportError 安全处理 httpx 异常
try:
    import httpx
    DEFAULT_RETRY_EXCEPTIONS = DEFAULT_RETRY_EXCEPTIONS + (
        httpx.ConnectError,
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
        httpx.WriteTimeout,
        httpx.PoolTimeout,
    )
except ImportError:
    pass


def async_retry(
    max_retries: int = 2,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    retry_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    log_prefix: str = ""
):
    """异步重试装饰器（指数退避）

    Args:
        max_retries: 最大重试次数（不含首次调用）
        base_delay: 首次重试等待秒数
        max_delay: 最大等待秒数
        retry_exceptions: 需要重试的异常类型，默认为网络相关异常
        log_prefix: 日志前缀（方便定位）
    """
    if retry_exceptions is None:
        retry_exceptions = DEFAULT_RETRY_EXCEPTIONS

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retry_exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        prefix = f"[{log_prefix}]" if log_prefix else ""
                        logger.warning(
                            f"{prefix} {func.__name__} 第{attempt + 1}次失败 "
                            f"({type(e).__name__}: {str(e)[:80]})，"
                            f"{delay:.1f}s 后重试..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        prefix = f"[{log_prefix}]" if log_prefix else ""
                        logger.error(
                            f"{prefix} {func.__name__} 重试{max_retries}次后仍失败: "
                            f"{type(e).__name__}: {str(e)[:120]}"
                        )
            raise last_exception
        return wrapper
    return decorator


def sync_retry(
    max_retries: int = 2,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    retry_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    log_prefix: str = ""
):
    """同步重试装饰器（指数退避），用于非 async 函数

    Args:
        max_retries: 最大重试次数（不含首次调用）
        base_delay: 首次重试等待秒数
        max_delay: 最大等待秒数
        retry_exceptions: 需要重试的异常类型
        log_prefix: 日志前缀
    """
    import time

    if retry_exceptions is None:
        retry_exceptions = DEFAULT_RETRY_EXCEPTIONS

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retry_exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        prefix = f"[{log_prefix}]" if log_prefix else ""
                        logger.warning(
                            f"{prefix} {func.__name__} 第{attempt + 1}次失败 "
                            f"({type(e).__name__}: {str(e)[:80]})，"
                            f"{delay:.1f}s 后重试..."
                        )
                        time.sleep(delay)
                    else:
                        prefix = f"[{log_prefix}]" if log_prefix else ""
                        logger.error(
                            f"{prefix} {func.__name__} 重试{max_retries}次后仍失败: "
                            f"{type(e).__name__}: {str(e)[:120]}"
                        )
            raise last_exception
        return wrapper
    return decorator
