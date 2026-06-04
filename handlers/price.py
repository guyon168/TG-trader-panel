"""报价命令: /p — 始终同时显示现货+合约价格"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from handlers import BaseHandler
from utils.helpers import escape_markdown

logger = logging.getLogger(__name__)


class PriceHandler(BaseHandler):
    """报价命令处理"""

    async def price(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/p <币种> — 同时显示现货和合约价格"""
        if not await self._check_auth(update, context):
            return
        if not context.args:
            return await self._reply(update, "❌ 使用方法: /p <币种>\n示例: /p BTC")

        symbol = context.args[0].upper()
        client = self.account_manager.get_client(update.effective_chat.id)
        if not client:
            return await self._reply(update, "❌ 请先选择账户")

        spot_price = None
        future_price = None

        # 始终同时获取现货和合约价格
        try:
            spot_price = client.get_price(symbol, mode_override='spot')
        except Exception as e:
            logger.warning(f"获取 {symbol} 现货价格失败: {str(e)}")

        try:
            future_price = client.get_price(symbol, mode_override='future')
        except Exception as e:
            logger.warning(f"获取 {symbol} 合约价格失败: {str(e)}")

        if spot_price is None and future_price is None:
            return await self._reply(update, f"❌ 无法获取 {symbol} 价格")

        text = f"📊 **{escape_markdown(symbol)}** 实时报价：\n\n"
        if spot_price is not None:
            text += f"• 现货: `${spot_price:.2f}`\n"
        else:
            text += "• 现货: ❌ 获取失败\n"
        if future_price is not None:
            text += f"• 合约: `${future_price:.2f}`\n"
        else:
            text += "• 合约: ❌ 获取失败\n"

        if spot_price is not None and future_price is not None:
            diff = future_price - spot_price
            diff_pct = (diff / spot_price) * 100 if spot_price > 0 else 0
            text += f"\n📊 价差: `{diff:.2f}` ({diff_pct:+.4f}%)"

        await self._reply(update, text, parse_mode='Markdown')
