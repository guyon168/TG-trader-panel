"""/margin 命令: 设置合约杠杆和保证金模式"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from handlers import BaseHandler, _is_network_error

logger = logging.getLogger(__name__)


class MarginHandler(BaseHandler):
    """杠杆/保证金模式设置"""

    async def margin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/margin <币种> <杠杆倍数> [isolated|cross]"""
        if not await self._check_auth(update, context):
            return

        client = self.account_manager.get_client(update.effective_chat.id)
        if not client:
            return await self._reply(update, "❌ 请先使用 /switch 选择账户")

        if getattr(client, 'mode', 'spot') != 'future':
            return await self._reply(update, "❌ /margin 仅适用于合约模式，请先切换到合约")

        if not context.args or len(context.args) < 2:
            return await self._reply(
                update,
                "📐 **杠杆设置**\n\n"
                "用法: `/margin <币种> <杠杆倍数> [isolated|cross]`\n\n"
                "示例:\n"
                "• `/margin btc 5 isolated` — BTC 5倍逐仓\n"
                "• `/margin eth 10 cross` — ETH 10倍全仓\n"
                "• `/margin bnb 3` — BNB 3倍（保持当前保证金模式）",
                parse_mode='Markdown'
            )

        symbol = context.args[0].upper()
        try:
            leverage = int(context.args[1])
            if leverage < 1 or leverage > 125:
                return await self._reply(update, "❌ 杠杆倍数需在 1-125 之间")
        except ValueError:
            return await self._reply(update, "❌ 杠杆倍数需为整数")

        margin_mode = context.args[2].lower() if len(context.args) > 2 else client.margin_mode
        if margin_mode not in ('isolated', 'cross'):
            return await self._reply(update, "❌ 保证金模式需为 isolated 或 cross")

        try:
            result = client.apply_leverage(symbol, leverage, margin_mode)
            text = (
                f"✅ **杠杆设置成功**\n\n"
                f"• 币种: `{symbol}`\n"
                f"• 杠杆: `{result['leverage']}x`\n"
                f"• 模式: `{result['margin_mode']}`\n"
                f"• 交易对: `{result['symbol']}`"
            )
            await self._reply(update, text, parse_mode='Markdown')
        except Exception as e:
            if _is_network_error(e):
                await self._reply(update, "🌐 设置杠杆失败：网络连接超时，请稍后重试")
            else:
                await self._reply(update, f"❌ 设置失败: {str(e)}")

    async def posmode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/posmode [net_mode|long_short_mode] — 查询或切换持仓模式"""
        if not await self._check_auth(update, context):
            return

        client = self.account_manager.get_client(update.effective_chat.id)
        if not client:
            return await self._reply(update, "❌ 请先使用 /switch 选择账户")

        if getattr(client, 'mode', 'spot') != 'future':
            return await self._reply(update, "❌ /posmode 仅适用于合约模式")

        # 不带参数 = 查询
        if not context.args:
            try:
                current = client.get_position_mode()
                label_map = {'net_mode': '单向持仓', 'long_short_mode': '双向持仓'}
                label = label_map.get(current, current)
                text = (
                    f"📐 **持仓模式**\n\n"
                    f"当前模式: **{label}** (`{current}`)\n\n"
                    f"切换命令:\n"
                    f"• `/posmode net_mode` — 单向持仓\n"
                    f"• `/posmode long_short_mode` — 双向持仓\n\n"
                    f"💡 切换前需先平掉所有仓位"
                )
                return await self._reply(update, text, parse_mode='Markdown')
            except Exception as e:
                return await self._reply(update, f"❌ 查询失败: {str(e)}")

        # 带参数 = 切换
        target = context.args[0].lower()
        if target not in ('net_mode', 'long_short_mode'):
            return await self._reply(update, "❌ 仅支持 net_mode 或 long_short_mode")

        try:
            res = client.set_position_mode(target)
            label = '单向持仓' if target == 'net_mode' else '双向持仓'
            await self._reply(update,
                f"✅ 已切换为 **{label}** (`{target}`)\n"
                f"💡 /posmode 可随时查询当前模式")
        except Exception as e:
            if _is_network_error(e):
                await self._reply(update, "🌐 切换持仓模式失败：网络连接超时")
            else:
                await self._reply(update, f"❌ 切换失败: {str(e)}")
