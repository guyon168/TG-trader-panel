"""查询命令: /balance, /position, /history, /orders — 修复 BUG-7"""
import logging
from typing import Dict, Any
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from handlers import BaseHandler, _is_network_error
from utils.helpers import escape_markdown

logger = logging.getLogger(__name__)


class QueryHandler(BaseHandler):
    """查询类命令处理"""

    async def balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/balance [币种]"""
        if not await self._check_auth(update, context):
            return
        client = self.account_manager.get_client(update.effective_chat.id)
        if not client:
            return await self._reply(update, "❌ 请先使用 /switch 选择账户")
        target_ccy = context.args[0].upper() if context.args else None

        try:
            balance = client.get_balance()
            if target_ccy:
                total = balance['total'].get(target_ccy, 0)
                if total <= 0 and target_ccy != 'USDT':
                    return await self._reply(update, f"🔍 账户中未持有 {target_ccy}")
                free = balance['free'].get(target_ccy, 0)
                locked = balance['used'].get(target_ccy, 0)

                # BUG-7 修复: get_price 传入 mode 参数
                value_usd = (total if target_ccy in ['USDT', 'BUSD', 'USDC', 'DAI']
                             else (total * client.get_price(target_ccy) if total > 0 else 0))
                text = (f"💰 **{target_ccy} 余额详情**\n\n"
                        f"• 总计: `{total:.8f}`\n• 可用: `{free:.8f}`\n• 锁定: `{locked:.8f}`\n")
                if value_usd > 0:
                    text += f"• 估值: `${value_usd:.2f} USDT`"
                return await self._reply(update, text, parse_mode='Markdown')

            text = f"💰 **{client.name}** 账户余额：\n\n"
            has_balance = False
            total_equity_usd = 0
            items = []

            for currency, total in balance['total'].items():
                if total <= 0:
                    continue
                free = balance['free'].get(currency, 0)
                locked = balance['used'].get(currency, 0)
                try:
                    # BUG-7 修复: get_price 传入 mode 参数
                    value_usd = (total if currency in ['USDT', 'BUSD', 'USDC', 'DAI']
                                else total * client.get_price(currency))
                except Exception:
                    value_usd = 0

                total_equity_usd += value_usd
                if currency != 'USDT' and value_usd < 1.0:
                    continue
                items.append({'ccy': currency, 'total': total, 'free': free,
                             'locked': locked, 'usd': value_usd})

            items.sort(key=lambda x: x['usd'], reverse=True)
            for item in items:
                locked_str = (f" (锁定: {item['locked']:.4f})" if item['locked'] > 0 else "")
                text += f"• **{item['ccy']}**: {item['total']:.4f} (${item['usd']:.2f}){locked_str}\n"
                has_balance = True

            text += f"\n💵 **估算总资产**: `${total_equity_usd:.2f} USDT`"
            if not has_balance and total_equity_usd < 1.0:
                text = f"💰 **{client.name}** 账户余额：\n\n暂无显著余额 (>1 USDT)"
            await self._reply(update, text[:3900] + ("\n...(更多小额资产已省略)" if len(text) > 4000 else ""),
                             parse_mode='Markdown')
        except Exception as e:
            if _is_network_error(e):
                await self._reply(update, "🌐 查询余额失败：网络连接超时，请稍后重试")
            else:
                await self._reply(update, f"❌ 查询失败: {str(e)}")

    async def position(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/position — 现货显示余额+可用，合约显示多空+PnL"""
        if not await self._check_auth(update, context):
            return
        client = self.account_manager.get_client(update.effective_chat.id)
        if not client:
            return await self._reply(update, "❌ 请先使用 /switch 选择账户")

        try:
            positions = client.get_positions()
            if not positions:
                return await self._reply(update, "📊 当前无持仓")

            is_spot = getattr(client, 'mode', 'future') == 'spot'

            if is_spot:
                await self._show_spot_position(update, client, positions)
            else:
                await self._show_futures_position(update, positions)
        except Exception as e:
            if _is_network_error(e):
                await self._reply(update, "🌐 查询持仓失败：网络连接超时，请稍后重试")
            else:
                await self._reply(update, f"❌ 查询失败: {str(e)}")

    async def _show_spot_position(self, update: Update, client, positions: list) -> None:
        """现货持仓：显示总余额 + 可用余额，按 USD 估值降序"""
        # 一次性拉取全市场报价
        try:
            tickers = client._sdk.client.get_all_tickers()
            price_map = {t['symbol']: float(t['price']) for t in tickers}
        except Exception:
            price_map = {}

        STABLECOINS = {'USDT', 'USDC', 'BUSD', 'TUSD', 'FDUSD', 'DAI'}
        items = []
        total_usd = 0
        for pos in positions:
            ccy = pos['symbol']
            total = pos['contracts']
            free = pos.get('free_balance', total)
            locked = pos.get('locked_balance', 0)
            if ccy in STABLECOINS:
                usd_total = total
                usd_free = free
            elif price_map:
                price = price_map.get(f'{ccy}USDT', 0)
                usd_total = total * price
                usd_free = free * price
            else:
                usd_total = usd_free = 0
            total_usd += usd_total
            items.append({'ccy': ccy, 'total': total, 'free': free,
                         'locked': locked, 'usd_total': usd_total, 'usd_free': usd_free})

        items.sort(key=lambda x: x['usd_total'], reverse=True)

        text = f"💰 **{client.name}** 现货持仓\n\n"
        for item in items:
            lock_hint = f" | 🔒 {item['locked']:.4f}" if item['locked'] > 0 else ""
            text += (f"• **{item['ccy']}**: {item['total']:.6g}"
                    f" (${item['usd_total']:.2f}){lock_hint}\n"
                    f"  可用: {item['free']:.6g} (${item['usd_free']:.2f})\n\n")
        text += f"💵 **总估值**: ${total_usd:.2f}"

        await self._reply(update, text[:3900], parse_mode='Markdown')

    async def _show_futures_position(self, update: Update, positions: list) -> None:
        """合约持仓：多空方向 + 开仓均价 + 未实现盈亏"""
        text = "📊 当前持仓：\n\n"
        for pos in positions:
            side_emoji = ("🟢 多" if pos['is_long']
                         else ("🔴 空" if pos['side'] != 'NET' else "⚪️"))
            pnl_emoji = ("📈" if pos['unrealized_pnl'] > 0
                        else "📉" if pos['unrealized_pnl'] < 0 else "➖")
            text += f"• **{escape_markdown(pos['display_symbol'])}** {side_emoji}\n"
            text += f"  数量: {pos['contracts']} {pos['unit']} | 杠杆: {pos['leverage']}x | {pos['margin_mode']}\n"
            text += f"  开仓均价: {pos['entry_price']:.4f}\n"
            text += f"  价值: {pos['notional']:.2f} USDT\n"
            text += f"  盈亏: {pnl_emoji} {pos['unrealized_pnl']:.2f} USDT\n\n"
        await self._reply(update, text, parse_mode='Markdown')

    async def history(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/history [币种]"""
        if not await self._check_auth(update, context):
            return
        client = self.account_manager.get_client(update.effective_chat.id)
        if not client:
            return await self._reply(update, "❌ 请先选择账户")

        symbol = context.args[0] if context.args else None

        try:
            history_data = client.get_positions_history(symbol)
            if not history_data:
                return await self._reply(update, "📜 暂无历史仓位记录")

            is_spot = getattr(client, 'mode', 'future') == 'spot'
            text = "📜 **最近成交记录 (30条)**\n\n" if is_spot else "📜 **最近历史仓位 (30条)**\n\n"

            for pos in history_data:
                if is_spot:
                    text += self._format_spot_history_line(pos)
                else:
                    text += self._format_futures_history_line(pos)
            await self._reply(update, text, parse_mode='Markdown')
        except Exception as e:
            if _is_network_error(e):
                await self._reply(update, "🌐 查询历史失败：网络连接超时，请稍后重试")
            else:
                await self._reply(update, f"❌ 查询失败: {str(e)}")

    async def ctval(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/ctVal <币种> — 查询合约面值"""
        if not await self._check_auth(update, context):
            return
        if not context.args:
            return await self._reply(update, "📐 **合约面值查询**\n\n用法: `/ctVal <币种>`\n示例: `/ctVal btc`")

        client = self.account_manager.get_client(update.effective_chat.id)
        if not client:
            return await self._reply(update, "❌ 请先选择账户")

        symbol = context.args[0].upper()
        try:
            info = client.get_ctval_info(symbol)
            price_str = f"{info['mark_price']:,.2f}" if info['mark_price'] > 0 else "获取失败"
            fv = info['face_value']
            text = (
                f"📐 **{info['inst_id']}** 合约面值\n\n"
                f"• 每张: `{info['ct_val']}` 个/张\n"
                f"• 标记价格: `${price_str}`\n"
                f"• 每张价值: `${fv:,.2f}`\n\n"
                f"💡 OKX合约下单数量为**张数**，\n"
                f"如 `/m buy btc 1` = 买入 1 张 ≈ ${fv:,.2f}"
            )
            await self._reply(update, text, parse_mode='Markdown')
        except Exception as e:
            if _is_network_error(e):
                await self._reply(update, "🌐 查询面值失败：网络连接超时")
            else:
                await self._reply(update, f"❌ 查询失败: {str(e)}")

    def _format_spot_history_line(self, pos: Dict[str, Any]) -> str:
        """格式化单条现货成交记录"""
        side = pos.get('side', '').upper()
        side_label = "🟢 买入" if side == 'BUY' else "🔴 卖出" if side == 'SELL' else f"⚪️ {side}"
        price = pos.get('openAvgPx', 0)
        qty = pos.get('sz', 0)
        notional = price * qty
        trade_time = (datetime.fromtimestamp(pos['openTime'] / 1000).strftime('%m-%d %H:%M')
                      if pos.get('openTime') and pos['openTime'] > 1000000000 else "未知")

        line = f"• **{escape_markdown(pos['display_symbol'])}** {side_label} (SPOT)\n"
        line += f"  数量: {qty} {pos['unit']}\n"
        line += f"  价格: {price:,.2f} USDT\n"
        line += f"  成交额: {notional:,.2f} USDT\n"
        line += f"  时间: {trade_time}\n\n"
        return line

    def _format_futures_history_line(self, pos: Dict[str, Any]) -> str:
        """格式化单条合约历史 — 自动区分仓位级(OKX)和成交级(Binance)"""
        side = pos.get('side', '').upper()
        close_price = pos.get('closeAvgPx', 0) or 0
        is_position = close_price > 0  # 有平仓均价 → 仓位级数据
        type_label = pos.get('type_label', '')

        if is_position:
            if side == 'LONG':
                direction = f"🟢 多单-{type_label}" if type_label else "🟢 多单-已平仓"
            elif side == 'SHORT':
                direction = f"🔴 空单-{type_label}" if type_label else "🔴 空单-已平仓"
            else:
                direction = f"⚪️ {side}"
        else:
            direction = "🟢 买入" if side == 'BUY' else "🔴 卖出" if side == 'SELL' else f"⚪️ {side}"

        mgn = pos.get('mgnMode', '')
        mgn_label = "逐仓" if mgn == 'isolated' else "全仓" if mgn == 'cross' else mgn
        trade_time = (datetime.fromtimestamp(pos['openTime'] / 1000).strftime('%m-%d %H:%M')
                      if pos.get('openTime') and pos['openTime'] > 1000000000 else "未知")

        line = f"• **{escape_markdown(pos['display_symbol'])}** {direction} ({mgn_label})\n"

        if is_position:
            close_time = (datetime.fromtimestamp(pos['closeTime'] / 1000).strftime('%m-%d %H:%M')
                         if pos.get('closeTime') and pos['closeTime'] > 1000000000 else "未知")
            pnl = pos.get('pnl', 0)
            pnl_pct = pos.get('pnlRatio', 0)
            pnl_emoji = "💰 +" if pnl > 0 else "💸" if pnl < 0 else "➖"
            line += f"  数量: {pos['sz']} {pos['unit']}\n"
            line += f"  开仓均价: {pos['openAvgPx']:.4f}\n  平仓均价: {close_price:.4f}\n"
            line += (f"  收益: {pnl_emoji} {pnl:.2f} USDT ({pnl_pct:.2f}%)\n"
                    f"  时间: {trade_time} ~ {close_time}\n\n")
        else:
            pnl = pos.get('pnl', 0)
            pnl_str = f" | 实现盈亏: ${pnl:+.2f}" if pnl != 0 else ""
            line += f"  数量: {pos['sz']} {pos['unit']} | 价格: {pos['openAvgPx']:.4f}{pnl_str}\n"
            line += f"  时间: {trade_time}\n\n"
        return line

    async def open_orders(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/orders [订单ID]"""
        if not await self._check_auth(update, context):
            return
        client = self.account_manager.get_client(update.effective_chat.id)
        if not client:
            return await self._reply(update, "❌ 请先使用 /switch 选择账户")

        target_id = context.args[0] if context.args else None
        try:
            orders = client.get_open_orders()
            if not orders:
                return await self._reply(update, "📋 当前无挂单")

            if target_id:
                target_order = next((o for o in orders if o['id'] == target_id), None)
                if not target_order:
                    return await self._reply(update, f"❌ 未找到订单 ID: `{target_id}`", parse_mode='Markdown')

                text = f"🔍 **订单深度详情 ({target_id})**\n\n"
                text += f"• **币种**: `{target_order['display_symbol']}`\n"
                text += f"• **方向**: `{target_order['side']}`\n"
                text += f"• **类型**: `{target_order['type']}`\n"
                text += f"• **状态**: `{target_order['status']}`\n\n🔧 **底层参数 (Raw Data):**\n"
                for k, v in target_order['raw'].items():
                    if v not in [None, '', '0', '0.0', '0.00000000']:
                        text += f"  > `{k}`: `{v}`\n"
                await self._reply(update, text, parse_mode='Markdown')
                return

            text = "📋 **当前挂单**：\n\n"
            for o in orders:
                price_text = (f"价格: {o['price']}" if o['price'] > 0
                             else f"类型: {escape_markdown(o['type'])}")
                trigger_text = o['trigger_info']
                if o['callback_str']:
                    trigger_text += f"\n  🔄 回调幅度: {o['callback_str']}"
                if o['active_px']:
                    trigger_text += f"\n  🎯 激活价: {o['active_px']}"

                text += f"• **{escape_markdown(o['display_symbol'])}** ({escape_markdown(o['type'])})\n"
                text += (f"  ID: `{o['id']}`\n  方向: {o['side']} | 数量: {o['amount']} {o['unit']}\n"
                        f"  {price_text}\n")
                if trigger_text:
                    text += f"  🔔 {escape_markdown(trigger_text).strip()}\n"
                text += f"  ⏰ 时间: {escape_markdown(o['time_str'])}\n\n"

            await self._reply(update, text[:3900], parse_mode='Markdown')
        except Exception as e:
            if _is_network_error(e):
                await self._reply(update, "🌐 查询挂单失败：网络连接超时，请稍后重试")
            else:
                await self._reply(update, f"❌ 查询失败: {str(e)}")
