"""TG-trader-panel 入口 + Handler 注册"""
import asyncio
import logging
import traceback
import yaml
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from core.logging_config import setup_logging
from core.account_manager import AccountManager
from handlers.menu import MenuHandler
from handlers.account import AccountHandler
from handlers.trade import TradeHandler
from handlers.tpsl import TPSLHandler
from handlers.trailing import TrailingHandler
from handlers.cancel import CancelHandler
from handlers.query import QueryHandler
from handlers.price import PriceHandler
from handlers.margin import MarginHandler

# 初始化日志系统（替代 basicConfig）
setup_logging()
logger = logging.getLogger(__name__)


async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """全局错误处理器 — 捕获未处理的异常，记录日志并通知用户"""
    error = context.error
    error_type = type(error).__name__ if error else "Unknown"

    # 判断是否为网络超时类异常
    is_timeout = any(kw in str(error_type).lower() for kw in ['timeout', 'connect', 'timed out'])
    is_network = any(kw in str(error).lower() for kw in ['timed out', 'connection', 'connecterror', 'network'])

    if is_timeout or is_network:
        logger.warning(f"🌐 网络异常 ({error_type}): {str(error)[:120]}")
        user_msg = "🌐 网络连接超时，请稍后重试（如持续超时请检查代理配置）"
    else:
        logger.error(f"❌ 未处理异常: {error_type}: {str(error)}", exc_info=error)
        user_msg = "❌ 处理请求时发生内部错误，请稍后重试"

    # 尝试通知用户
    if update and isinstance(update, Update):
        try:
            chat = update.effective_chat
            if chat:
                await context.bot.send_message(chat_id=chat.id, text=user_msg)
        except Exception as send_err:
            logger.error(f"全局错误处理器发送消息失败: {send_err}")


class TraderBot:
    def __init__(self, config_path: str = 'config.yaml'):
        self.config = self._load_config(config_path)
        self.account_manager = AccountManager(self.config)
        self.bot_token = self.config['telegram']['bot_token']
        self.proxy_url = self._build_proxy_url()

        # 构造 bot_config
        tg = self.config['telegram']
        bot_config = {
            'allowed_users': set(tg.get('allowed_users', [])),
            'allowed_chats': set(tg.get('allowed_chats', [])),
            'quick_symbols': tg.get('quick_symbols', ['BTC', 'ETH', 'SOL']),
            'quick_amounts': tg.get('quick_amounts', [10, 50, 100, 500]),
        }

        # 创建所有 Handler
        self.menu = MenuHandler(self.account_manager, bot_config)
        self.account = AccountHandler(self.account_manager, bot_config)
        self.trade = TradeHandler(self.account_manager, bot_config)
        self.tpsl = TPSLHandler(self.account_manager, bot_config)
        self.trailing = TrailingHandler(self.account_manager, bot_config)
        self.cancel = CancelHandler(self.account_manager, bot_config)
        self.query = QueryHandler(self.account_manager, bot_config)
        self.price = PriceHandler(self.account_manager, bot_config)
        self.margin = MarginHandler(self.account_manager, bot_config)

        # 注入 Handler 引用（MenuHandler 作为回调路由中心）
        self.menu.set_handlers({
            'query': self.query, 'cancel': self.cancel,
            'trade': self.trade, 'account': self.account,
        })

    def _load_config(self, config_path: str) -> dict:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _build_proxy_url(self) -> str | None:
        """从 config.yaml 构建 Telegram Bot API 代理 URL"""
        proxy_port = self.config.get('proxy', {}).get('port')
        if proxy_port:
            return f"http://127.0.0.1:{proxy_port}"
        return None

    def run(self):
        builder = ApplicationBuilder().token(self.bot_token)

        # 代理配置 — 同时应用到 Bot API 和 getUpdates
        if self.proxy_url:
            builder = builder.proxy(self.proxy_url)
            builder = builder.get_updates_proxy(self.proxy_url)
            logger.info(f"🌐 Telegram Bot API 使用代理: {self.proxy_url}")

        # 超时配置（秒）— 本地代理环境适当放宽
        builder = builder.connect_timeout(20)
        builder = builder.read_timeout(45)
        builder = builder.write_timeout(30)
        builder = builder.pool_timeout(10)
        # getUpdates 长轮询 — 给足时间等代理
        builder = builder.get_updates_connect_timeout(20)
        builder = builder.get_updates_read_timeout(90)
        builder = builder.get_updates_write_timeout(30)
        builder = builder.get_updates_pool_timeout(10)

        app = builder.build()

        # 全局错误处理器
        app.add_error_handler(global_error_handler)

        # 命令注册
        app.add_handler(CommandHandler('start', self.menu.start))
        app.add_handler(CommandHandler('help', self.menu.help_command))
        app.add_handler(CommandHandler('menu', self.menu.start))
        app.add_handler(CommandHandler('switch', self.account.switch_account))
        app.add_handler(CommandHandler('mode', self.account.switch_mode))
        app.add_handler(CommandHandler('accounts', self.account.list_accounts))
        app.add_handler(CommandHandler('status', self.account.status))
        app.add_handler(CommandHandler('market', self.trade.market_order))
        app.add_handler(CommandHandler('m', self.trade.market_order))
        app.add_handler(CommandHandler('limit', self.trade.limit_order))
        app.add_handler(CommandHandler('l', self.trade.limit_order))
        app.add_handler(CommandHandler('cancel', self.cancel.cancel_order))
        app.add_handler(CommandHandler('cancle', self.cancel.cancel_order))
        app.add_handler(CommandHandler('balance', self.query.balance))
        app.add_handler(CommandHandler('position', self.query.position))
        app.add_handler(CommandHandler('open_orders', self.query.open_orders))
        app.add_handler(CommandHandler('orders', self.query.open_orders))
        app.add_handler(CommandHandler('order', self.query.open_orders))
        app.add_handler(CommandHandler('history', self.query.history))
        app.add_handler(CommandHandler('tpsl', self.tpsl.set_tpsl))
        app.add_handler(CommandHandler('tp', self.tpsl.set_tpsl))
        app.add_handler(CommandHandler('sl', self.tpsl.set_tpsl))
        app.add_handler(CommandHandler('ts', self.trailing.set_trailing_stop))
        app.add_handler(CommandHandler('trailing', self.trailing.set_trailing_stop))
        app.add_handler(CommandHandler('p', self.price.price))
        app.add_handler(CommandHandler('margin', self.margin.margin))
        app.add_handler(CommandHandler('close', self.trade.close_position))
        app.add_handler(CommandHandler('ctval', self.query.ctval))
        app.add_handler(CommandHandler('ctVal', self.query.ctval))
        # 回调 & 未知命令
        app.add_handler(CallbackQueryHandler(self.menu.handle_callback))
        app.add_handler(MessageHandler(filters.COMMAND, self.menu.unknown))
        logger.info("🚀 机器人启动中...")
        self._run_polling_with_retry(app)

    @staticmethod
    def _run_polling_with_retry(app):
        """带指数退避的 polling，本地代理断连时自动恢复"""
        import time
        max_retries = 10
        base_delay = 3

        for retry in range(max_retries + 1):
            try:
                app.run_polling()
                return
            except Exception as e:
                if retry >= max_retries:
                    logger.critical(f"🚨 getUpdates 重试 {max_retries} 次仍失败: {type(e).__name__}: {str(e)[:200]}")
                    raise
                delay = min(base_delay * (2 ** retry), 120)
                logger.warning(
                    f"🌐 getUpdates 断连 ({type(e).__name__})，{delay}s 后第 {retry + 1}/{max_retries} 次重试...")
                time.sleep(delay)


if __name__ == '__main__':
    TraderBot().run()
