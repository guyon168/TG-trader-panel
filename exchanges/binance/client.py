"""Binance 交易所客户端主类 — 路由层"""
import logging
from decimal import Decimal, ROUND_DOWN
from typing import Dict, Optional, Any, List
from binance.client import Client
from core.base_client import BaseExchangeClient
from exchanges.binance.spot.query import BinanceSpotQueryMixin
from exchanges.binance.spot.history import BinanceSpotHistoryMixin
from exchanges.binance.spot.market import BinanceSpotMarketMixin
from exchanges.binance.spot.limit import BinanceSpotLimitMixin
from exchanges.binance.spot.tpsl import BinanceSpotTpslMixin
from exchanges.binance.spot.trailing import BinanceSpotTrailingMixin
from exchanges.binance.spot.cancel import BinanceSpotCancelMixin
from exchanges.binance.futures.query import BinanceFuturesQueryMixin
from exchanges.binance.futures.history import BinanceFuturesHistoryMixin
from exchanges.binance.futures.market import BinanceFuturesMarketMixin
from exchanges.binance.futures.limit import BinanceFuturesLimitMixin
from exchanges.binance.futures.tpsl import BinanceFuturesTpslMixin
from exchanges.binance.futures.trailing import BinanceFuturesTrailingMixin
from exchanges.binance.futures.cancel import BinanceFuturesCancelMixin

logger = logging.getLogger(__name__)


class BinanceClient(BinanceSpotQueryMixin,
                     BinanceSpotHistoryMixin,
                     BinanceSpotMarketMixin,
                     BinanceSpotLimitMixin,
                     BinanceSpotTpslMixin,
                     BinanceSpotTrailingMixin,
                     BinanceSpotCancelMixin,
                     BinanceFuturesQueryMixin,
                     BinanceFuturesHistoryMixin,
                     BinanceFuturesMarketMixin,
                     BinanceFuturesLimitMixin,
                     BinanceFuturesTpslMixin,
                     BinanceFuturesTrailingMixin,
                     BinanceFuturesCancelMixin,
                     BaseExchangeClient):
    """Binance 交易所客户端，通过 spot/ + futures/ Mixin 组合各功能模块"""

    exchange_name = 'binance'

    def __init__(self, api_key: str, api_secret: str,
                 testnet: bool = False, proxy: Optional[str] = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.proxy = proxy
        self.margin_mode = 'isolated'  # 默认逐仓，由 set_leverage_and_margin 更新

        requests_params = {}
        if self.proxy:
            requests_params['proxies'] = {'http': self.proxy, 'https': self.proxy}

        self.client = Client(self.api_key, self.api_secret,
                             requests_params=requests_params,
                             testnet=self.testnet)
        try:
            self.client.get_server_time()
        except Exception:
            pass
        logger.info(f"Binance Client 初始化成功 ({'Testnet' if testnet else 'Mainnet'})")

    # ———— 查询方法路由 ————

    def get_price(self, symbol: str, mode: str) -> float:
        """获取最新价格 — 路由到 spot 或 futures"""
        if mode == 'spot':
            return self.get_price_spot(symbol)
        return self.get_price_futures(symbol)

    def get_balance(self, mode: str) -> Dict[str, Any]:
        """获取账户余额 — 路由到 spot 或 futures"""
        if mode == 'spot':
            return self.get_balance_spot()
        return self.get_balance_futures()

    def get_positions(self, mode: str) -> List[Dict[str, Any]]:
        """获取持仓列表 — 路由到 spot 或 futures"""
        if mode == 'spot':
            return self.get_positions_spot()
        return self.get_positions_futures()

    def get_positions_history(self, symbol: Optional[str], mode: str) -> List[Dict[str, Any]]:
        """获取历史成交记录 — 路由到 spot 或 futures"""
        if mode == 'spot':
            return self.get_positions_history_spot(symbol)
        return self.get_positions_history_futures(symbol)

    def get_open_orders(self, symbol: Optional[str], mode: str) -> List[Dict[str, Any]]:
        """获取挂单 — 路由到 spot 或 futures"""
        if mode == 'spot':
            return self.get_open_orders_spot(symbol)
        return self.get_open_orders_futures(symbol)

    # ———— 下单方法路由 ————

    def place_market_order(self, symbol: str, side: str, amount: float,
                           is_usdt: bool, mode: str, leverage: int,
                           margin_mode: str) -> Dict[str, Any]:
        """市价下单 — 路由到 spot 或 futures"""
        if mode == 'spot':
            return self.place_market_order_spot(symbol, side, amount, is_usdt)
        return self.place_market_order_futures(symbol, side, amount, is_usdt, leverage, margin_mode)

    def place_limit_order(self, symbol: str, side: str, amount: float,
                          price: float, is_usdt: bool, mode: str,
                          leverage: int, margin_mode: str) -> Dict[str, Any]:
        """限价下单 — 路由到 spot 或 futures"""
        if mode == 'spot':
            return self.place_limit_order_spot(symbol, side, amount, price, is_usdt)
        return self.place_limit_order_futures(symbol, side, amount, price, is_usdt, leverage, margin_mode)

    def place_tpsl(self, symbol: str, side: str, amount: float,
                   tp: Optional[float], sl: Optional[float],
                   mode: str, margin_mode: str, reduce_only: bool = False) -> Dict[str, Any]:
        """止盈止损条件单 — 路由到 spot 或 futures"""
        if mode == 'spot':
            return self.place_tpsl_spot(symbol, side, amount, tp, sl)
        return self.place_tpsl_futures(symbol, side, amount, tp, sl, reduce_only)

    def place_trailing_stop(self, symbol: str, side: str, amount: float,
                            callback_ratio: float, active_px: Optional[float],
                            is_usdt: bool, mode: str, leverage: int,
                            margin_mode: str, reduce_only: bool = False) -> Dict[str, Any]:
        """移动止损 — 路由到 spot 或 futures"""
        if mode == 'spot':
            return self.place_trailing_stop_spot(symbol, side, amount, callback_ratio,
                                                  active_px, is_usdt)
        return self.place_trailing_stop_futures(symbol, side, amount, callback_ratio,
                                                 active_px, is_usdt, leverage, reduce_only)

    # ———— 平仓方法路由 ————

    def close_position(self, symbol: str, mode: str, margin_mode: str) -> Dict[str, Any]:
        """平仓 — 用 reduceOnly 市价单平掉所有仓位"""
        raw_s = self.format_symbol(symbol, 'future')
        from binance.exceptions import BinanceAPIException
        results = []
        for ps in ['LONG', 'SHORT']:
            try:
                # 获取持仓量
                positions = self.client.futures_position_information(symbol=raw_s)
                for p in positions:
                    pos_amt = float(p.get('positionAmt', 0))
                    pos_side = p.get('positionSide', 'BOTH')
                    if pos_amt == 0:
                        continue
                    if pos_side != 'BOTH' and pos_side != ps:
                        continue
                    # 反向市价单平仓
                    close_side = 'SELL' if float(pos_amt) > 0 else 'BUY'
                    close_params = {
                        'symbol': raw_s,
                        'side': close_side,
                        'type': 'MARKET',
                        'quantity': str(abs(pos_amt)),
                        'reduceOnly': 'true',
                    }
                    if pos_side != 'BOTH':
                        close_params['positionSide'] = pos_side
                    res = self.client.futures_create_order(**close_params)
                    results.append(res)
            except BinanceAPIException as e:
                if 'no position' not in str(e).lower():
                    raise
        if results:
            return {'code': '0', 'status': 'success', 'count': len(results)}
        raise Exception("未找到可平仓的持仓")

    def get_position_mode(self) -> str:
        """查询当前持仓模式"""
        res = self.client.futures_get_position_mode()
        dual = res.get('dualSidePosition', False)
        return 'long_short_mode' if dual else 'net_mode'

    def set_position_mode(self, pos_mode: str) -> Dict[str, Any]:
        """切换持仓模式"""
        if pos_mode == 'long_short_mode':
            dual = 'true'
        elif pos_mode == 'net_mode':
            dual = 'false'
        else:
            raise Exception("持仓模式仅支持 net_mode 或 long_short_mode")
        res = self.client.futures_change_position_mode(dualSidePosition=dual)
        return {'code': '0' if res.get('code') == 200 else '-1', 'pos_mode': pos_mode}

    # ———— 撤单方法路由 ————

    def cancel_orders(self, symbol: Optional[str], order_id: Optional[str],
                      mode: str) -> int:
        """撤销订单 — 路由到 spot 或 futures"""
        if mode == 'spot':
            return self.cancel_orders_spot(symbol, order_id)
        return self.cancel_orders_futures(symbol, order_id)

    # ———— 工具方法 ————

    def format_symbol(self, symbol: str, mode: str) -> str:
        """将用户输入的币种转为 Binance symbol 格式（现货合约统一）"""
        if not symbol:
            return ""
        s = symbol.upper().replace('/', '').replace(':', '').replace('-', '').replace(' ', '').replace('PERP', '')
        if not s.endswith('USDT') and s not in ['USDT', 'BUSD', 'USDC']:
            s += 'USDT'
        return s

    def calculate_quantity(self, symbol: str, money: float, price: float, mode: str) -> float:
        """根据 USDT 金额计算可下单数量（遵守交易所步长规则）"""
        raw_s = self.format_symbol(symbol, mode)
        exchange_info = self.client.futures_exchange_info() if mode == 'future' else self.client.get_exchange_info()
        symbol_info = next((s for s in exchange_info['symbols'] if s['symbol'] == raw_s), None)
        if not symbol_info:
            raise ValueError(f"未在 Binance 找到交易对: {raw_s}")

        lot_size = next(f for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE')
        step_size = Decimal(lot_size['stepSize']).normalize()
        min_qty = Decimal(lot_size['minQty'])

        quantity = Decimal(str(money)) / Decimal(str(price))
        quantity = (quantity / step_size).quantize(Decimal('1'), rounding=ROUND_DOWN) * step_size
        return float(max(quantity, min_qty))

    def set_leverage_and_margin(self, symbol: str, leverage: int, margin_mode: str) -> None:
        """设置合约杠杆和保证金模式（静默忽略重复设置错误）"""
        try:
            self.client.futures_change_leverage(symbol=symbol, leverage=leverage)
        except Exception as e:
            if "-4161" not in str(e):
                logger.warning(f"Binance 杠杆设置忽略: {str(e)}")
        try:
            self.client.futures_change_margin_type(symbol=symbol, marginType=margin_mode.upper())
        except Exception as e:
            if "-4048" not in str(e) and "-4046" not in str(e):
                logger.warning(f"Binance 保证金设置忽略: {str(e)}")
        self.margin_mode = margin_mode.lower()  # 记录当前保证金模式

    def set_leverage(self, symbol: str, leverage: int, margin_mode: str) -> Dict[str, Any]:
        """设置合约杠杆和保证金模式 — 用户主动调用，返回结果"""
        raw_s = self.format_symbol(symbol, 'future')
        try:
            self.client.futures_change_leverage(symbol=raw_s, leverage=leverage)
        except Exception as e:
            if "-4161" not in str(e):
                raise Exception(f"设置杠杆失败: {str(e)}")
        try:
            self.client.futures_change_margin_type(symbol=raw_s, marginType=margin_mode.upper())
        except Exception as e:
            err_str = str(e)
            if "-4048" not in err_str and "-4046" not in err_str:
                raise Exception(f"设置保证金模式失败: {err_str}")
        self.margin_mode = margin_mode.lower()
        return {'symbol': raw_s, 'leverage': leverage, 'margin_mode': margin_mode.upper()}
