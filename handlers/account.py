"""账户管理命令: /switch, /mode, /accounts, /status"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from handlers import BaseHandler

logger = logging.getLogger(__name__)


class AccountHandler(BaseHandler):
    """账户切换与状态查询处理"""

    async def switch_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/switch <交易所> <子账户ID> [模式]"""
        if not await self._check_auth(update, context):
            return
        if len(context.args) < 2:
            return await self._reply(update, "❌ 使用方法: /switch <交易所> <子账户ID> [模式]")
        exchange = context.args[0].lower()
        account_id = context.args[1]
        mode = context.args[2].lower() if len(context.args) > 2 else None
        if mode and mode not in ['spot', 'future']:
            return await self._reply(update, "❌ 模式只能是 spot (现货) 或 future (合约)")

        chat_id = update.effective_chat.id
        if self.account_manager.switch_account(chat_id, exchange, account_id, mode):
            info = self.account_manager.get_current_account_info(chat_id)
            testnet_tag = " (测试网)" if info.get('testnet') else ""
            await self._reply(update, f"✅ 成功切换到：\n账户: {info['name']}{testnet_tag}\n模式: {info['mode']}")
        else:
            available = self.account_manager.list_available_accounts_with_info()
            text = "❌ 账户不存在！\n\n可用账户：\n"
            for ex, accs in available.items():
                text += f"🔹 {ex.upper()}:\n"
                for a in accs:
                    tag = " [TEST]" if a['testnet'] else ""
                    text += f"  • {a['id']} ({a['name']}){tag}\n"
            await self._reply(update, text)

    async def switch_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/mode <spot|future>"""
        if not await self._check_auth(update, context):
            return
        if len(context.args) != 1 or context.args[0] not in ['spot', 'future']:
            return await self._reply(update, "❌ 使用方法: /mode <spot|future>")
        if self.account_manager.switch_mode(update.effective_chat.id, context.args[0]):
            await self._reply(update, f"✅ 已切换到 {'现货' if context.args[0] == 'spot' else '合约'} 模式")
        else:
            await self._reply(update, "❌ 请先使用 /switch 选择账户")

    async def list_accounts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/accounts"""
        if not await self._check_auth(update, context):
            return
        available = self.account_manager.list_available_accounts_with_info()
        if not available:
            return await self._reply(update, "❌ 没有配置任何账户")
        text = "📋 可用账户：\n\n"
        for exchange, accounts in available.items():
            text += f"🔹 {exchange.upper()}:\n"
            for acc in accounts:
                tag = " [TEST]" if acc['testnet'] else ""
                text += f"  • {acc['id']}: {acc['name']}{tag}\n"
        await self._reply(update, text)

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/status"""
        if not await self._check_auth(update, context):
            return
        info = self.account_manager.get_current_account_info(update.effective_chat.id)
        if not info:
            return await self._reply(update, "⚠️ 尚未选择账户，请使用 /switch")
        await self._reply(update,
            f"📍 当前状态：\n交易所: {info['exchange']}\n账户: {info['account']}\n模式: {'现货' if info['mode'] == 'spot' else '合约'}")
