"""主菜单 + 回调路由 — 修复 BUG-6: handle_callback split 问题"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from handlers import BaseHandler

logger = logging.getLogger(__name__)


class MenuHandler(BaseHandler):
    """主菜单显示与回调路由中心"""

    def __init__(self, account_manager, bot_config):
        super().__init__(account_manager, bot_config)
        self._handlers = {}

    def set_handlers(self, handlers: dict):
        """注入其他 handler 引用，用于回调路由"""
        self._handlers = handlers

    # ======================== 命令入口 ========================

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update, context):
            return
        await self.show_main_menu(update, context)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update, context):
            return
        help_text = """
📋 **使用帮助**

━━━ 📌 账户管理 ━━━
/start, /menu — 主菜单面板
/switch <交易所> <子账户ID> [spot|future] — 切换账户
/mode <spot|future> — 切换现货/合约模式
/accounts — 列出所有可用账户
/status — 查看当前账户状态

━━━ ⚙️ 合约设置 ━━━
/margin <币种> <杠杆> [isolated|cross] — 设置合约杠杆/保证金模式
  示例: `/margin btc 5 isolated` — BTC 5倍逐仓
  示例: `/margin eth 10 cross` — ETH 10倍全仓
/ctVal <币种> — 查询合约面值（每张价值）
  示例: `/ctVal btc` — 查看 BTC-USDT-SWAP 每张价值

💡 **OKX 合约注意**: /m、/l 等下单命令的数量是**合约张数**，
  不是币种数量。如 `/m buy btc 1` = 买入 1 张 BTC 合约。
  用 /ctVal 可查每张价值。

━━━ 💰 查询命令 ━━━
/balance [币种] — 查询余额（指定币种显示详情）
/position — 查询当前持仓
  • 现货：总余额 + 可用余额 + USD估值
  • 合约：多空方向 + 开仓均价 + 未实现盈亏
/orders [订单ID] — 查询挂单（指定ID显示底层参数）
/history [币种] — 查询历史成交记录
  • 现货：需指定币种，未指定时根据现货余额查询
  • 合约：未指定币种时自动查询全部
/p <币种> — 同时查看现货 & 合约价格 + 价差

━━━ ⚡️ 下单命令 ━━━
/m <buy|sell> <币种> <数量/金额> [tp=价格] [sl=价格]
  市价下单，可附带止盈止损
  示例: `/m buy BTC 100u`
  示例: `/m sell ETH 0.5 tp=3500 sl=2800`

/l <buy|sell> <币种> <数量/金额> <价格> [tp=价格] [sl=价格]
  限价下单，可附带止盈止损
  示例: `/l sell BTC 100u 100000`

━━━ 🎯 止盈止损 ━━━
/tp <buy|sell> <币种> <数量> <止盈价> [--reduceonly]
  单独设置止盈；合约可加--reduceonly 只减仓不开新仓
  示例: `/tp sell BTC 0.05 75000`
  示例: `/tp sell BTC 0.05 75000 --reduceonly`

/sl <buy|sell> <币种> <数量> <止损价> [--reduceonly]
  单独设置止损；合约可加--reduceonly 只减仓不开新仓
  示例: `/sl sell BTC 0.05 60000`

/tpsl <buy|sell> <币种> <数量> tp=价格 sl=价格 [--reduceonly]
  双向止盈止损（省略方向时自动从持仓判断）；合约可加--reduceonly 只减仓不开新仓
  示例: `/tpsl sell BTC 0.1 tp=75000 sl=60000`

/ts [buy|sell] <币种> <数量/金额> <回调幅度> [px=激活价] [--reduceonly]
  移动止损；合约可加--reduceonly 只减仓不开新仓
  示例: `/ts ETH 2 0.01 px=3100`
  示例: `/ts buy ETH 500u 0.01 px=2100`
  示例: `/ts sell bnb 3 590 --reduceonly`

💡 **合约模式提示**:
- 末尾加 `--reduceonly` 表示只减仓（不开新仓），不加则默认可开新仓
- 适用于 /tp、/sl、/tpsl、/ts 四个命令

━━━ 📤 平仓命令 ━━━
/close <币种> — 一键平仓（市价反向单，双向持仓自动处理）
  示例: `/close eth` — 平掉 ETH 所有持仓

━━━ 🚫 撤单命令 ━━━
/cancel <ALL|币种|订单ID> — 撤销挂单
  示例: `/cancel ALL` — 撤销全部
  示例: `/cancel BTC` — 撤销 BTC 相关挂单
  示例: `/cancel 12345678` — 撤销指定订单

💡 **通用提示**:
- 金额末尾加 `u` 或 `usdt` 自动识别为 USDT 计价
- 合约下单自动同步杠杆和保证金模式
- 省略方向时，/tpsl 和 /ts 会从持仓自动判断
- 使用 /help 随时调出此说明
        """
        await self._reply(update, help_text, parse_mode='Markdown')

    async def unknown(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            return
        await self._reply(update, "❌ 未知命令，使用 /start 查看帮助")

    # ======================== 主菜单 ========================

    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        info = self.account_manager.get_current_account_info(chat_id)

        status_text = "❌ 尚未选择账户"
        keyboard = []
        if info:
            mode_name = "现货" if info['mode'] == 'spot' else "合约"
            testnet_tag = " (TESTNET)" if info.get('testnet') else ""
            margin_text = (f" ({'逐仓' if info.get('margin_mode') == 'isolated' else '全仓'})" 
                          if info['mode'] == 'future' else "")
            status_text = f"✅ {info['name']}{testnet_tag}\n📍 模式: {mode_name}{margin_text}"

            keyboard.append([InlineKeyboardButton("⚡️ 快捷下单", callback_data="menu_trade")])
            mode_btns = [InlineKeyboardButton("⚙️ 切换现货/合约", callback_data="menu_modes")]
            if info['mode'] == 'future':
                mode_btns.append(InlineKeyboardButton("🛡 切换全仓/逐仓", callback_data="menu_margin_modes"))
                mode_btns.append(InlineKeyboardButton("⬆️ 设置杠杆", callback_data="menu_leverage"))
                mode_btns.append(InlineKeyboardButton("📐 合约面值", callback_data="menu_ctval"))
            keyboard.append(mode_btns)

            keyboard.append([
                InlineKeyboardButton("💰 查询余额", callback_data="action_balance"),
                InlineKeyboardButton("📊 查询持仓", callback_data="action_position")
            ])
            keyboard.append([
                InlineKeyboardButton("📜 历史仓位", callback_data="action_history"),
                InlineKeyboardButton("📋 查询挂单", callback_data="action_open_orders")
            ])
            keyboard.append([
                InlineKeyboardButton("🚫 撤销全部", callback_data="action_cancel_all"),
                InlineKeyboardButton("❓ 帮助说明", callback_data="menu_help")
            ])
            keyboard.append([
                InlineKeyboardButton("🔄 切换账户", callback_data="menu_accounts")
            ])
        else:
            keyboard.append([InlineKeyboardButton("🔄 选择账户", callback_data="menu_accounts")])
            keyboard.append([InlineKeyboardButton("❓ 帮助说明", callback_data="menu_help")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        text = f"🚀 **多交易所下单面板**\n\n{status_text}\n\n请选择操作："

        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
            else:
                await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        except Exception as e:
            err_str = str(e)
            if "Message is not modified" in err_str:
                return  # 消息内容无变化，静默忽略
            # 网络超时给用户反馈
            if any(kw in err_str.lower() for kw in ('timed out', 'timeout', 'connect', 'network')):
                logger.warning(f"🌐 主菜单发送网络异常: {err_str[:100]}")
                try:
                    if update.callback_query:
                        await update.callback_query.answer("🌐 网络超时，请稍后重试", show_alert=True)
                    else:
                        await update.message.reply_text("🌐 菜单加载超时，请稍后重试 /start")
                except Exception:
                    pass
            else:
                logger.error(f"显示主菜单失败: {err_str}")

    # ======================== 回调路由 ========================

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """回调路由中心 — 修复 BUG-6: 使用 split('_', 2) 和前缀匹配"""
        query = update.callback_query
        try:
            await query.answer()
        except Exception:
            pass

        data = query.data
        chat_id = update.effective_chat.id

        # ---- 菜单导航 ----
        if data == "menu_main":
            await self.show_main_menu(update, context)
        elif data == "menu_accounts":
            await self._show_accounts(update, context)
        elif data == "menu_modes":
            await self._show_modes(update, context)
        elif data == "menu_margin_modes":
            await self._show_margin_modes(update, context)
        elif data == "menu_leverage":
            await self._show_leverage_prompt(update, context)
        elif data == "menu_ctval":
            await self._show_ctval_prompt(update, context)
        elif data == "margin_cross":
            await self._set_margin_mode_callback(update, context, 'cross')
        elif data == "margin_isolated":
            await self._set_margin_mode_callback(update, context, 'isolated')
        elif data == "menu_trade":
            await self._show_trade_symbols(update, context)
        elif data == "menu_help":
            await self.help_command(update, context)

        # ---- BUG-6 修复: 使用 split("_", 2) 避免 account_id 中的下划线被误拆 ----
        elif data.startswith("switch_"):
            parts = data.split("_", 2)
            if len(parts) >= 3:
                _, exchange, account_id = parts
                if self.account_manager.switch_account(chat_id, exchange, account_id):
                    await self.show_main_menu(update, context)
                else:
                    await query.edit_message_text("❌ 切换失败")

        elif data.startswith("mode_"):
            mode = data.split("_")[1]
            if self.account_manager.switch_mode(chat_id, mode):
                info = self.account_manager.get_current_account_info(chat_id)
                if info.get('testnet'):
                    await query.answer(f"已切换到 {mode} 模式", show_alert=True)
                await self.show_main_menu(update, context)
            else:
                await query.edit_message_text("❌ 请先选择账户")

        elif data.startswith("margin_"):
            margin_mode = data.split("_")[1]
            if self.account_manager.switch_margin_mode(chat_id, margin_mode):
                await self.show_main_menu(update, context)
            else:
                await query.edit_message_text("❌ 请先选择账户并切换到合约模式")

        # ---- 快捷交易路由 ----
        elif data.startswith("trade_symbol_"):
            symbol = data.split("_")[2]
            await self._show_trade_side(update, context, symbol)
        elif data.startswith("trade_side_"):
            parts = data.split("_")
            symbol = parts[2]
            side = parts[3]
            await self._show_trade_amount(update, context, symbol, side)
        elif data.startswith("trade_amount_"):
            parts = data.split("_")
            symbol = parts[2]
            side = parts[3]
            amount = parts[4]
            await self._execute_quick_trade(update, context, symbol, side, amount)

        # ---- 操作回调 ----
        elif data == "action_balance":
            await self._safe_call(update, self._handlers['query'].balance(update, context), "查询余额")
            await self.show_main_menu(update, context)
        elif data == "action_position":
            await self._safe_call(update, self._handlers['query'].position(update, context), "查询持仓")
            await self.show_main_menu(update, context)
        elif data == "action_history":
            await self._safe_call(update, self._handlers['query'].history(update, context), "查询历史")
            await self.show_main_menu(update, context)
        elif data == "action_open_orders":
            await self._safe_call(update, self._handlers['query'].open_orders(update, context), "查询挂单")
            await self.show_main_menu(update, context)
        elif data == "action_cancel_all":
            context.args = ['ALL']
            await self._safe_call(update, self._handlers['cancel'].cancel_order(update, context), "撤销全部")
            await self.show_main_menu(update, context)

    # ======================== 菜单子页面 ========================

    async def _show_accounts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        available = self.account_manager.list_available_accounts_with_info()
        keyboard = []
        for exchange, accounts in available.items():
            for acc in accounts:
                testnet_tag = " [TEST]" if acc['testnet'] else ""
                btn_text = f"🔹 {acc['name']}{testnet_tag}"
                keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"switch_{exchange}_{acc['id']}")])
        keyboard.append([InlineKeyboardButton("⬅️ 返回主菜单", callback_data="menu_main")])
        await update.callback_query.edit_message_text("请选择要切换的账户：", reply_markup=InlineKeyboardMarkup(keyboard))

    async def _show_modes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("📈 现货 (Spot)", callback_data="mode_spot"),
             InlineKeyboardButton("📉 合约 (Future)", callback_data="mode_future")],
            [InlineKeyboardButton("⬅️ 返回主菜单", callback_data="menu_main")]
        ]
        await update.callback_query.edit_message_text("⚙️ 请选择交易模式：", reply_markup=InlineKeyboardMarkup(keyboard))

    async def _show_margin_modes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("🛡 全仓 (Cross)", callback_data="margin_cross"),
             InlineKeyboardButton("🛡 逐仓 (Isolated)", callback_data="margin_isolated")],
            [InlineKeyboardButton("⬅️ 返回主菜单", callback_data="menu_main")]
        ]
        await update.callback_query.edit_message_text("🛡 请选择合约保证金模式：", reply_markup=InlineKeyboardMarkup(keyboard))

    async def _show_leverage_prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """显示杠杆设置引导"""
        keyboard = [[InlineKeyboardButton("⬅️ 返回主菜单", callback_data="menu_main")]]
        chat_id = update.effective_chat.id
        info = self.account_manager.get_current_account_info(chat_id)
        client = self.account_manager.get_client(chat_id)
        leverage = getattr(client, 'leverage', 3) if client else 3
        margin_mode = info.get('margin_mode', 'isolated') if info else 'isolated'
        text = (
            f"⬆️ **杠杆设置**\n\n"
            f"当前默认杠杆: `{leverage}x`  |  保证金: `{margin_mode}`\n\n"
            f"使用命令修改:\n"
            f"`/margin <币种> <杠杆> [isolated|cross]`\n\n"
            f"示例:\n"
            f"• `/margin btc 5 isolated`\n"
            f"• `/margin eth 10 cross`"
        )
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    async def _show_ctval_prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """显示合约面值查询引导"""
        keyboard = [[InlineKeyboardButton("⬅️ 返回主菜单", callback_data="menu_main")]]
        text = (
            f"📐 **合约面值查询**\n\n"
            f"查询合约每张价值 = ctVal × 标记价格\n\n"
            f"使用命令:\n"
            f"`/ctVal <币种>`\n\n"
            f"示例:\n"
            f"• `/ctVal btc` — BTC-USDT-SWAP 面值\n"
            f"• `/ctVal eth` — ETH-USDT-SWAP 面值\n\n"
            f"💡 OKX 合约下单数量为**张数**，\n"
            f"如 `/m buy btc 1` = 买入 1 张"
        )
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    async def _set_margin_mode_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, mode: str):
        """处理全仓/逐仓切换回调"""
        client = self.account_manager.get_client(update.effective_chat.id)
        if client:
            client.set_margin_mode('', mode)
            await update.callback_query.answer(f"✅ 已切换为 {'逐仓(Isolated)' if mode == 'isolated' else '全仓(Cross)'}")
        await self.show_main_menu(update, context)

    async def _show_trade_symbols(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [[InlineKeyboardButton(f"🚀 {sym}", callback_data=f"trade_symbol_{sym}")]
                     for sym in self.quick_symbols]
        keyboard.append([InlineKeyboardButton("⬅️ 返回主菜单", callback_data="menu_main")])
        await update.callback_query.edit_message_text("⚡️ 请选择交易币种：", reply_markup=InlineKeyboardMarkup(keyboard))

    async def _show_trade_side(self, update: Update, context: ContextTypes.DEFAULT_TYPE, symbol: str):
        keyboard = [
            [InlineKeyboardButton("🟢 买入 (Buy)", callback_data=f"trade_side_{symbol}_buy"),
             InlineKeyboardButton("🔴 卖出 (Sell)", callback_data=f"trade_side_{symbol}_sell")],
            [InlineKeyboardButton("⬅️ 返回上级", callback_data="menu_trade")]
        ]
        await update.callback_query.edit_message_text(
            f"⚡️ 币种: {symbol}\n请选择交易方向：", reply_markup=InlineKeyboardMarkup(keyboard))

    async def _show_trade_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                  symbol: str, side: str):
        keyboard, row = [], []
        for amount in self.quick_amounts:
            row.append(InlineKeyboardButton(f"{amount}u", callback_data=f"trade_amount_{symbol}_{side}_{amount}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("⬅️ 返回上级", callback_data=f"trade_symbol_{symbol}")])
        side_name = "买入" if side == "buy" else "卖出"
        await update.callback_query.edit_message_text(
            f"⚡️ 币种: {symbol}\n⚡️ 方向: {side_name}\n请选择下单金额 (USDT)：",
            reply_markup=InlineKeyboardMarkup(keyboard))

    async def _execute_quick_trade(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                   symbol: str, side: str, amount: str):
        client = self.account_manager.get_client(update.effective_chat.id)
        if not client:
            return await update.callback_query.edit_message_text("❌ 请先选择账户")
        try:
            order = client.market_order(symbol, side, float(amount), is_usdt=True)
            side_name = "买入" if side == "buy" else "卖出"
            await update.callback_query.edit_message_text(
                f"✅ 快捷下单成功！\n交易所: {client.exchange_name.upper()}\n币种: {symbol}\n方向: {side_name}\n金额: {amount} USDT\n订单ID: {order['id']}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ 返回主菜单", callback_data="menu_main")]]))
        except Exception as e:
            await update.callback_query.edit_message_text(
                f"❌ 下单失败: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ 返回主菜单", callback_data="menu_main")]]))
