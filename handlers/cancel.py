"""撤单命令: /cancel"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from handlers import BaseHandler, _is_network_error

logger = logging.getLogger(__name__)


class CancelHandler(BaseHandler):
    """撤单命令处理"""

    async def cancel_order(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/cancel <ALL|币种|订单ID>"""
        if not await self._check_auth(update, context):
            return
        if not context.args:
            return await self._reply(update, "❌ 使用方法: /cancel <ALL|币种|订单ID>")

        client = self.account_manager.get_client(update.effective_chat.id)
        if not client:
            return await self._reply(update, "❌ 请先使用 /switch 选择账户")

        try:
            target = context.args[0]
            if target.upper() == 'ALL':
                count = client.cancel_all_orders()
                await self._reply(update, f"✅ 已撤销全部 {count} 个挂单")
            else:
                msg = client.cancel_target(target)
                await self._reply(update, msg, parse_mode='Markdown')
        except Exception as e:
            if _is_network_error(e):
                await self._reply(update, "🌐 撤单失败：网络连接超时，请稍后重试或用 /orders 确认状态")
            else:
                await self._reply(update, f"❌ 撤单失败: {str(e)}")
