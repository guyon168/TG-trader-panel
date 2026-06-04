"""移动止损命令: /ts"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from handlers import BaseHandler, _is_network_error
from utils.helpers import parse_amount

logger = logging.getLogger(__name__)


class TrailingHandler(BaseHandler):
    """移动止损命令处理"""

    async def set_trailing_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/ts [buy|sell] <币种> <数量/金额> <回调幅度> [px=激活价] [--reduceonly]"""
        if not await self._check_auth(update, context):
            return
        args = list(context.args)
        if len(args) < 3:
            return await self._reply(update,
                "❌ 使用方法: /ts [buy|sell] <币种> <数量/金额> <回调幅度> [px=激活价] [--reduceonly]")

        # 解析 --reduceonly 标志
        reduce_only = False
        if '--reduceonly' in [a.lower() for a in args]:
            reduce_only = True
            args = [a for a in args if a.lower() != '--reduceonly']

        side_input = None
        if args[0].lower() in ['buy', 'sell']:
            side_input = args[0].upper()
            args = args[1:]

        symbol = args[0].upper()
        amount_str = args[1].lower()
        try:
            amount, is_usdt = parse_amount(amount_str)
            callback_ratio = float(args[2])
        except (ValueError, IndexError):
            return await self._reply(update, "❌ 数量和回调幅度必须是数字")

        active_px = None
        for arg in args[3:]:
            if arg.startswith('active_px=') or arg.startswith('px='):
                active_px = float(arg.split('=')[1])

        client = self.account_manager.get_client(update.effective_chat.id)
        if not client:
            return await self._reply(update, "❌ 请先选择账户")

        try:
            order_side = side_input
            if not order_side:
                for pos in client.get_positions():
                    if pos['symbol'].replace('-', '').upper().startswith(symbol.replace('-', '').upper()):
                        order_side = 'SELL' if pos['is_long'] else 'BUY'
                        symbol = pos['symbol']
                        break
            if not order_side:
                return await self._reply(update, f"⚠️ 未找到 {symbol} 持仓方向")

            res = client.place_trailing_stop(symbol, order_side, amount, callback_ratio,
                                             active_px, is_usdt, reduce_only)
            ro_tag = " (只减仓)" if reduce_only else ""
            await self._reply(update,
                f"✅ 移动止损设置成功{ro_tag}！\n"
                f"订单ID: {res['id']}\n币种: {res['symbol']}\n方向: {order_side}\n"
                f"数量: {res['amount']} {res.get('unit', '')}\n"
                f"回调幅度: {callback_ratio * 100}% | 激活价: {active_px or '立即激活'}")
        except Exception as e:
            if _is_network_error(e):
                await self._reply(update, "🌐 移动止损设置失败：网络连接超时，请确认是否已生效后用 /orders 检查")
            else:
                await self._reply(update, f"❌ 设置失败: {str(e)}")
