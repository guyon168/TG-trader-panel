"""止盈止损命令: /tp, /sl, /tpsl — 修复 BUG-8"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from handlers import BaseHandler, _is_network_error
from utils.helpers import parse_amount

logger = logging.getLogger(__name__)


class TPSLHandler(BaseHandler):
    """止盈止损命令处理"""

    async def set_tpsl(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/tp, /sl, /tpsl 命令统一入口"""
        if not await self._check_auth(update, context):
            return
        args = list(context.args)
        # BUG-8 修复: 使用精确命令名比较，不再用 endswith
        command = update.message.text.split()[0].lower()
        command = command.split('@')[0]

        # 解析 --reduceonly 标志
        reduce_only = False
        if '--reduceonly' in [a.lower() for a in args]:
            reduce_only = True
            args = [a for a in args if a.lower() != '--reduceonly']

        if len(args) < 3:
            return

        side_input = None
        if args[0].lower() in ['buy', 'sell']:
            side_input = args[0].upper()
            args = args[1:]

        symbol = args[0].upper()
        amount_str = args[1].lower()

        # 剥离 'u' 和 'usdt'
        if amount_str.endswith('usdt'):
            amount_str = amount_str[:-4]
        elif amount_str.endswith('u'):
            amount_str = amount_str[:-1]

        try:
            amount = float(amount_str)
        except ValueError:
            return await self._reply(update, "❌ 数量必须是数字")

        tp = sl = None
        # BUG-8 修复: 用直接比较替代 endswith
        if command == '/tp':
            tp = float(args[2])
        elif command == '/sl':
            sl = float(args[2])
        else:
            # /tpsl 命令
            for arg in args[2:]:
                if arg.startswith('tp='):
                    tp = float(arg.split('=')[1])
                elif arg.startswith('sl='):
                    sl = float(arg.split('=')[1])

        if tp is None and sl is None:
            return await self._reply(update, "❌ 请至少指定 tp 或 sl 其中之一")

        client = self.account_manager.get_client(update.effective_chat.id)
        if not client:
            return await self._reply(update, "❌ 请先选择账户")

        try:
            final_side = side_input
            if not final_side:
                for pos in client.get_positions():
                    if pos['symbol'].replace('-', '').upper().startswith(symbol.replace('-', '').upper()):
                        final_side = 'SELL' if pos['is_long'] else 'BUY'
                        symbol = pos['symbol']
                        break
            if not final_side:
                return await self._reply(update, f"❌ 未找到 {symbol} 持仓方向。")

            res = client.create_tpsl_orders(symbol, final_side, amount, tp, sl, reduce_only)

            is_success = (res.get('code') == '0' or 'orderId' in res or 'oco' in res
                         or 'tp' in res or 'sl' in res or 'algoId' in res
                         or res.get('status') == 'success')

            ro_tag = " (只减仓)" if reduce_only else ""
            text = f"📊 为 {symbol} {final_side} 设置结果{ro_tag}：\n"
            if is_success:
                if tp:
                    text += f"✅ 止盈设置成功: {tp}\n"
                if sl:
                    text += f"✅ 止损设置成功: {sl}\n"
            else:
                text += f"❌ 设置失败: {res.get('msg', '未知错误')}"
            await self._reply(update, text)
        except Exception as e:
            if _is_network_error(e):
                await self._reply(update, "🌐 止盈止损设置失败：网络连接超时，请确认是否已生效后用 /orders 检查")
            else:
                await self._reply(update, f"❌ 设置失败: {str(e)}")
