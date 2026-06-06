"""ExchangeClient 编排层 — 通过多态替代 if/else"""
import logging
from typing import Dict, Optional, Any, List
from core.base_client import BaseExchangeClient
from exchanges.binance import BinanceClient
from exchanges.okx import OKXClient

logger = logging.getLogger(__name__)


class ExchangeClient:
    """交易所客户端编排层

    持有 BaseExchangeClient 实例（self._sdk），通过多态调用替代 if/else。
    工厂方法 _create_sdk() 根据交易所名创建实例。
    """

    def __init__(self, exchange_name: str, account_id: str,
                 config: Dict[str, Any], proxy_port: Optional[int] = None):
        self.exchange_name = exchange_name.lower()
        self.account_id = account_id
        self.mode = config.get('mode', 'spot')
        self.leverage = config.get('leverage', 1)
        self.margin_mode = config.get('margin_mode', 'isolated')
        self.testnet = config.get('testnet', False)
        self.name = config.get('name', f"{exchange_name}.{account_id}")

        proxy_url = f"http://127.0.0.1:{proxy_port}" if proxy_port else None
        self._sdk: BaseExchangeClient = self._create_sdk(config, proxy_url)

    def _create_sdk(self, config: Dict[str, Any], proxy_url: Optional[str]) -> BaseExchangeClient:
        """工厂方法：根据交易所名创建 SDK 实例"""
        if self.exchange_name == 'okx':
            return OKXClient(
                config.get('api_key'), config.get('api_secret'),
                config.get('passphrase'), self.testnet, proxy_url)
        elif self.exchange_name == 'binance':
            return BinanceClient(
                config.get('api_key'), config.get('api_secret'),
                self.testnet, proxy_url)
        else:
            raise ValueError(f"不支持的交易所: {self.exchange_name}")

    # ======================== 模式设置 ========================

    def set_mode(self, mode: str) -> None:
        """设置交易模式（现货/合约）"""
        self.mode = mode
        logger.info(f"[{self.name}] 切换交易模式为: {mode}")

    def set_leverage(self, leverage: int) -> None:
        """设置本地杠杆倍数（不调用交易所 API）"""
        self.leverage = leverage
        logger.info(f"[{self.name}] 设置杠杆倍数为: {leverage}x")

    def set_margin_mode(self, symbol: str, margin_mode: str) -> bool:
        """设置本地保证金模式（不调用交易所 API）"""
        if self.mode != 'future':
            return False
        self.margin_mode = margin_mode.lower()
        logger.info(f"[{self.name}] 设置本地保证金模式状态为 {margin_mode}")
        return True

    def apply_leverage(self, symbol: str, leverage: int, margin_mode: str) -> Dict[str, Any]:
        """设置合约杠杆+保证金模式（调用交易所 API 并更新本地状态）"""
        if self.mode != 'future':
            raise Exception("仅合约模式支持设置杠杆")
        result = self._sdk.set_leverage(symbol, leverage, margin_mode)
        # 同步本地状态
        self.leverage = leverage
        self.margin_mode = margin_mode.lower()
        logger.info(f"[{self.name}] 已设置 {symbol} 杠杆: {leverage}x {margin_mode}")
        return result

    def get_ctval_info(self, symbol: str) -> Dict[str, Any]:
        """查询合约面值信息（仅 OKX 合约支持）"""
        if self.mode != 'future':
            raise Exception("仅合约模式支持查询面值")
        if self.exchange_name != 'okx':
            raise Exception("合约面值查询仅支持 OKX")
        return self._sdk.get_ctval_info(symbol)

    def close_position(self, symbol: str) -> Dict[str, Any]:
        """平仓（支持双向持仓模式）"""
        if self.mode != 'future':
            raise Exception("仅合约模式支持平仓")
        return self._sdk.close_position(symbol, self.mode, self.margin_mode)

    def get_position_mode(self) -> str:
        """查询当前持仓模式"""
        if self.mode != 'future':
            raise Exception("仅合约模式支持持仓模式")
        return self._sdk.get_position_mode()

    def set_position_mode(self, pos_mode: str) -> Dict[str, Any]:
        """切换持仓模式"""
        if self.mode != 'future':
            raise Exception("仅合约模式支持持仓模式")
        return self._sdk.set_position_mode(pos_mode)

    # ======================== 查询 ========================

    def get_price(self, symbol: str, mode_override: Optional[str] = None) -> float:
        """获取当前价格，支持 mode_override 供 /p 命令使用（BUG-7 修复）"""
        mode = mode_override if mode_override is not None else self.mode
        return self._sdk.get_price(symbol, mode)

    def get_balance(self) -> Dict[str, Any]:
        """获取余额"""
        return self._sdk.get_balance(self.mode)

    def get_positions(self) -> List[Dict[str, Any]]:
        """获取持仓"""
        return self._sdk.get_positions(self.mode)

    def get_positions_history(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取历史仓位记录"""
        return self._sdk.get_positions_history(symbol, self.mode)

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取当前挂单"""
        return self._sdk.get_open_orders(symbol, self.mode)

    # ======================== 撤单 ========================

    def cancel_all_orders(self) -> int:
        """一键撤销当前模式下的所有挂单"""
        return self._sdk.cancel_orders(None, None, self.mode)

    def cancel_target(self, target: str) -> str:
        """智能路由撤单请求（处理 ID vs 币种的差异）"""
        target = target.upper()
        is_order_id = target.isdigit() and len(target) > 5

        orders = self.get_open_orders()
        ex_name = self.exchange_name.upper()

        if is_order_id:
            target_order = next((o for o in orders if str(o.get('id')) == target), None)
            symbol = target_order['symbol'] if target_order else None

            try:
                count = self._sdk.cancel_orders(symbol, target, self.mode)
                if count > 0:
                    sym_display = f" ({target_order['display_symbol']})" if target_order else ""
                    return f"✅ 已撤销 {ex_name} 订单: `{target}`{sym_display}"
            except Exception as e:
                return f"❌ 撤销 {ex_name} 订单 `{target}` 异常: {str(e)}"

            return f"❌ 撤单失败：未找到有效订单 `{target}` 或已被交易所拒绝"
        else:
            sym_keyword = target.replace('-', '').replace('/', '').upper()
            matched_syms = set([
                o['symbol'] for o in orders
                if o['symbol'].replace('-', '').upper().startswith(sym_keyword)
            ])

            if not matched_syms:
                try:
                    c = self._sdk.cancel_orders(target, None, self.mode)
                    if c > 0:
                        return f"✅ 强制尝试撤销 `{target}`，共清理 {c} 个"
                except Exception as e:
                    return f"❌ 撤销 `{target}` 失败: {str(e)}"
                return f"❌ 未找到与 `{target}` 相关的挂单"

            count = 0
            for sym in matched_syms:
                try:
                    count += self._sdk.cancel_orders(sym, None, self.mode)
                except Exception:
                    pass

            if count > 0:
                return f"✅ 已批量撤销 `{target}` 相关的 {count} 个挂单"
            return f"❌ 尝试撤销 `{target}` 失败"

    # ======================== 下单 ========================

    def market_order(self, symbol: str, side: str, amount: float,
                     is_usdt: bool = False,
                     tp: Optional[float] = None, sl: Optional[float] = None) -> Dict[str, Any]:
        """市价单路由（主单成功后附带 TP/SL）"""
        res = self._sdk.place_market_order(
            symbol, side, amount, is_usdt, self.mode, self.leverage, self.margin_mode)
        if tp or sl:
            try:
                self._sdk.place_tpsl(
                    res['symbol'], side, res['amount'], tp, sl, self.mode, self.margin_mode)
                res['tp_sl_success'] = True
            except Exception as e:
                res['tp_sl_error'] = str(e)
        return res

    def limit_order(self, symbol: str, side: str, amount: float, price: float,
                    is_usdt: bool = False,
                    tp: Optional[float] = None, sl: Optional[float] = None) -> Dict[str, Any]:
        """限价单路由（主单成功后附带 TP/SL）"""
        res = self._sdk.place_limit_order(
            symbol, side, amount, price, is_usdt, self.mode, self.leverage, self.margin_mode)
        if tp or sl:
            try:
                self._sdk.place_tpsl(
                    res['symbol'], side, res['amount'], tp, sl, self.mode, self.margin_mode)
                res['tp_sl_success'] = True
            except Exception as e:
                res['tp_sl_error'] = str(e)
        return res

    def create_tpsl_orders(self, symbol: str, side: str, amount: float,
                            tp: Optional[float] = None, sl: Optional[float] = None,
                            reduce_only: bool = False) -> Dict[str, Any]:
        """独立调用 TP/SL 接口（供 /tpsl 补单指令使用）"""
        try:
            res = self._sdk.place_tpsl(symbol, side, amount, tp, sl, self.mode, self.margin_mode, reduce_only)
            res['code'] = '0'  # 向前兼容 handler 的判断逻辑
            return res
        except Exception as e:
            return {'msg': str(e), 'code': '-1'}

    def place_trailing_stop(self, symbol: str, side: str, amount: float,
                            callback_ratio: float, active_px: Optional[float] = None,
                            is_usdt: bool = False, reduce_only: bool = False) -> Dict[str, Any]:
        """移动止盈止损路由"""
        return self._sdk.place_trailing_stop(
            symbol, side, amount, callback_ratio, active_px,
            is_usdt, self.mode, self.leverage, self.margin_mode, reduce_only)
