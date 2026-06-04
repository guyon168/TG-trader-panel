"""命令处理层 — BaseHandler 基类"""
import logging
from typing import Dict, Optional, Set
from telegram import Update
from telegram.ext import ContextTypes
from core.account_manager import AccountManager

logger = logging.getLogger(__name__)

# 网络超时相关异常类名关键词
_TIMEOUT_KEYWORDS = ('timeout', 'timed out', 'connecterror', 'connectionerror',
                     'connectionreset', 'brokenpipe')
_NETWORK_KEYWORDS = ('network', 'connection', 'proxy', 'resolve', 'dns')


def _is_network_error(error: Exception) -> bool:
    """判断异常是否为网络/超时类"""
    err_str = f"{type(error).__name__} {str(error)}".lower()
    return any(kw in err_str for kw in _TIMEOUT_KEYWORDS + _NETWORK_KEYWORDS)


class BaseHandler:
    """所有命令处理器的基类，提供权限检查、回复、超时反馈等通用方法"""

    def __init__(self, account_manager: AccountManager, bot_config: Dict):
        self.account_manager = account_manager
        self.allowed_users: Set[int] = bot_config.get('allowed_users', set())
        self.allowed_chats: Set[int] = bot_config.get('allowed_chats', set())
        self.quick_symbols = bot_config.get('quick_symbols', ['BTC', 'ETH', 'SOL'])
        self.quick_amounts = bot_config.get('quick_amounts', [10, 50, 100, 500])

    def _is_authorized(self, update: Update) -> bool:
        """检查用户是否有权限"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        if user_id in self.allowed_users:
            return True
        if chat_id in self.allowed_chats:
            return True
        logger.warning(f"未授权访问: 用户 {user_id}, 聊天 {chat_id}")
        return False

    async def _reply(self, update: Update, text: str, **kwargs):
        """通用回复方法，处理消息和回调（带超时重试一次）"""
        try:
            if update.callback_query:
                await update.callback_query.message.reply_text(text, **kwargs)
            else:
                await update.message.reply_text(text, **kwargs)
        except Exception as e:
            if _is_network_error(e):
                # 网络超时：重试一次
                logger.warning(f"📤 发送消息网络异常，1s后重试: {type(e).__name__}: {str(e)[:80]}")
                import asyncio
                await asyncio.sleep(1)
                try:
                    if update.callback_query:
                        await update.callback_query.message.reply_text(text, **kwargs)
                    else:
                        await update.message.reply_text(text, **kwargs)
                    return
                except Exception:
                    pass
            logger.error(f"⚠️ 发送消息失败: {type(e).__name__}: {str(e)[:120]}")

    async def _safe_call(self, update: Update, coro, error_prefix: str = "操作"):
        """安全执行异步操作：捕获异常并给用户友好反馈

        区分网络超时和业务错误，给出不同的提示文本。
        """
        try:
            return await coro
        except Exception as e:
            if _is_network_error(e):
                msg = f"🌐 {error_prefix}失败：网络连接超时，请稍后重试"
                logger.warning(f"🌐 {error_prefix}超时: {type(e).__name__}: {str(e)[:100]}")
            else:
                msg = f"❌ {error_prefix}失败: {str(e)[:100]}"
                logger.error(f"❌ {error_prefix}异常: {type(e).__name__}: {str(e)[:120]}")
            await self._reply(update, msg)
            return None

    async def _check_auth(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """检查权限并回复"""
        if not self._is_authorized(update):
            await self._reply(update, "❌ 你没有权限使用此机器人")
            return False
        return True
