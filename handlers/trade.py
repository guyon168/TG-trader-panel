"""交易命令: /m, /l + 快捷下单回调"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from handlers import BaseHandler, _is_network_error
from utils.helpers import parse_amount

logger = logging.getLogger(__name__)


class TradeHandler(BaseHandler):
    """市价单和限价单命令处理"""

    async def market_order(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/m <buy|sell> <币种> <数量/金额> [tp=价格] [sl=价格]"""
        if not await self._check_auth(update, context):
            return
        args = context.args
        if len(args) < 3:
            return await self._reply(update, "❌ 使用方法: /market <buy|sell> <币种> <数量/金额> [tp=价格] [sl=价格]")

        side = args[0].lower()
        symbol = args[1].upper()
        amount_str = args[2].lower()
        if side not in ['buy', 'sell']:
            return await self._reply(update, "❌ 方向只能是 buy 或 sell")

        tp = sl = None
        for arg in args[3:]:
            if arg.startswith('tp='):
                tp = float(arg.split('=')[1])
            elif arg.startswith('sl='):
                sl = float(arg.split('=')[1])

        try:
            amount, is_usdt = parse_amount(amount_str)
        except ValueError:
            return await self._reply(update, "❌ 数量必须是数字")

        client = self.account_manager.get_client(update.effective_chat.id)
        if not client:
            return await self._reply(update, "❌ 请先选择账户")

        try:
            order = client.market_order(symbol, side, amount, is_usdt=is_usdt, tp=tp, sl=sl)
            text = (f"✅ 市价单成功！\n订单ID: {order['id']}\n方向: {side}\n"
                    f"币种: {order['symbol']}\n下单量: {order['amount']} {order.get('unit', '')}")
            if 'tp_sl_error' in order:
                text += f"\n❌ 止盈止损附带失败: {order['tp_sl_error']}"
            elif tp or sl:
                text += "\n✅ 止盈止损附带成功"
            await self._reply(update, text)
        except Exception as e:
            if _is_network_error(e):
                await self._reply(update, "🌐 市价下单失败：网络连接超时，请确认是否已成交后用 /orders 检查")
            else:
                await self._reply(update, f"❌ 下单失败: {str(e)}")

    async def limit_order(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/l <buy|sell> <币种> <数量/金额> <价格> [tp=价格] [sl=价格]"""
        if not await self._check_auth(update, context):
            return
        args = context.args
        if len(args) < 4:
            return await self._reply(update, "❌ 使用方法: /limit <buy|sell> <币种> <数量/金额> <价格> [tp=价格] [sl=价格]")

        side = args[0].lower()
        symbol = args[1].upper()
        amount_str = args[2].lower()
        if side not in ['buy', 'sell']:
            return await self._reply(update, "❌ 方向只能是 buy 或 sell")

        tp = sl = None
        for arg in args[4:]:
            if arg.startswith('tp='):
                tp = float(arg.split('=')[1])
            elif arg.startswith('sl='):
                sl = float(arg.split('=')[1])

        try:
            amount, is_usdt = parse_amount(amount_str)
            price = float(args[3])
        except ValueError:
            return await self._reply(update, "❌ 数量和价格必须是数字")

        client = self.account_manager.get_client(update.effective_chat.id)
        if not client:
            return await self._reply(update, "❌ 请先选择账户")

        try:
            order = client.limit_order(symbol, side, amount, price, is_usdt=is_usdt, tp=tp, sl=sl)
            text = (f"✅ 限价单成功！\n订单ID: {order['id']}\n方向: {side}\n"
                    f"币种: {order['symbol']}\n下单量: {order['amount']} {order.get('unit', '')}\n价格: {price}")
            if 'tp_sl_error' in order:
                text += f"\n❌ 止盈止损附带失败: {order['tp_sl_error']}"
            elif tp or sl:
                text += "\n✅ 止盈止损附带成功"
            await self._reply(update, text)
        except Exception as e:
            if _is_network_error(e):
                await self._reply(update, "🌐 限价下单失败：网络连接超时，请确认是否已挂单后用 /orders 检查")
            else:
                await self._reply(update, f"❌ 下单失败: {str(e)}")

    async def close_position(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/close <币种> — 平仓"""
        if not await self._check_auth(update, context):
            return
        if not context.args:
            return await self._reply(update, "❌ 使用方法: /close <币种>\n示例: /close eth")

        client = self.account_manager.get_client(update.effective_chat.id)
        if not client:
            return await self._reply(update, "❌ 请先选择账户")

        symbol = context.args[0].upper()
        try:
            res = client.close_position(symbol)
            await self._reply(update,
                f"✅ {symbol} 平仓指令已提交\n"
                f"💡 用 /position 确认是否平仓成功")
        except Exception as e:
            if _is_network_error(e):
                await self._reply(update, "🌐 平仓失败：网络连接超时")
            else:
                await self._reply(update, f"❌ 平仓失败: {str(e)}")
