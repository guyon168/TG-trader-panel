"""OKX 交易所客户端主类 — 路由层"""
import logging
from typing import Dict, Optional, Any, List
import okx.Account as Account
import okx.Trade as Trade
import okx.MarketData as MarketData
import okx.PublicData as PublicData
from core.base_client import BaseExchangeClient
from exchanges.okx.adapter import OKXAdapter
from exchanges.okx.ctval_cache import CTValCache
from exchanges.okx.posside_detector import PosSideDetector
from exchanges.okx.spot.query import OKXSpotQueryMixin
from exchanges.okx.spot.history import OKXSpotHistoryMixin
from exchanges.okx.spot.market import OKXSpotMarketMixin
from exchanges.okx.spot.limit import OKXSpotLimitMixin
from exchanges.okx.spot.tpsl import OKXSpotTpslMixin
from exchanges.okx.spot.trailing import OKXSpotTrailingMixin
from exchanges.okx.spot.cancel import OKXSpotCancelMixin
from exchanges.okx.futures.query import OKXFuturesQueryMixin
from exchanges.okx.futures.history import OKXFuturesHistoryMixin
from exchanges.okx.futures.market import OKXFuturesMarketMixin
from exchanges.okx.futures.limit import OKXFuturesLimitMixin
from exchanges.okx.futures.tpsl import OKXFuturesTpslMixin
from exchanges.okx.futures.trailing import OKXFuturesTrailingMixin
from exchanges.okx.futures.cancel import OKXFuturesCancelMixin

logger = logging.getLogger(__name__)


class OKXClient(OKXSpotQueryMixin,
                OKXSpotHistoryMixin,
                OKXSpotMarketMixin,
                OKXSpotLimitMixin,
                OKXSpotTpslMixin,
                OKXSpotTrailingMixin,
                OKXSpotCancelMixin,
                OKXFuturesQueryMixin,
                OKXFuturesHistoryMixin,
                OKXFuturesMarketMixin,
                OKXFuturesLimitMixin,
                OKXFuturesTpslMixin,
                OKXFuturesTrailingMixin,
                OKXFuturesCancelMixin,
                BaseExchangeClient):
    """OKX 交易所客户端，通过 spot/ + futures/ Mixin 组合各功能模块"""

    exchange_name = 'okx'

    def __init__(self, api_key: str, api_secret: str, passphrase: str,
                 testnet: bool = False, proxy: Optional[str] = None):
        self.testnet = testnet
        self.flag = '1' if testnet else '0'
        self._account_api = Account.AccountAPI(
            api_key, api_secret, passphrase,
            use_server_time=False, flag=self.flag, proxy=proxy)
        self._trade_api = Trade.TradeAPI(
            api_key, api_secret, passphrase,
            use_server_time=False, flag=self.flag, proxy=proxy)
        self._market_api = MarketData.MarketAPI(
            api_key, api_secret, passphrase,
            use_server_time=False, flag=self.flag, proxy=proxy)
        self._public_api = PublicData.PublicAPI(flag=self.flag, proxy=proxy)

        # 适配层：将来切换 CLI/MCP 只需替换 adapter 实现
        self._adapter = OKXAdapter(self._trade_api, self._account_api, self._market_api, self._public_api)

        # BUG-1 修复: posSide 动态检测
        self._posside_detector = PosSideDetector(self._adapter)
        # BUG-2 修复: ctVal 缓存
        self._ctval_cache = CTValCache(self._adapter)

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
        return self.place_tpsl_futures(symbol, side, amount, tp, sl, margin_mode, reduce_only)

    def place_trailing_stop(self, symbol: str, side: str, amount: float,
                            callback_ratio: float, active_px: Optional[float],
                            is_usdt: bool, mode: str, leverage: int,
                            margin_mode: str, reduce_only: bool = False) -> Dict[str, Any]:
        """移动止损 — 路由到 spot 或 futures"""
        if mode == 'spot':
            return self.place_trailing_stop_spot(symbol, side, amount, callback_ratio,
                                                  active_px, is_usdt)
        return self.place_trailing_stop_futures(symbol, side, amount, callback_ratio,
                                                 active_px, is_usdt, leverage, margin_mode, reduce_only)

    # ———— 撤单方法路由 ————

    def cancel_orders(self, symbol: Optional[str], order_id: Optional[str],
                      mode: str) -> int:
        """撤销订单 — 路由到 spot 或 futures"""
        if mode == 'spot':
            return self.cancel_orders_spot(symbol, order_id)
        return self.cancel_orders_futures(symbol, order_id)

    # ———— 工具方法 ————

    def format_symbol(self, symbol: str, mode: str) -> str:
        """将用户输入的币种转为 OKX instId 格式"""
        if not symbol:
            return ""
        s = symbol.upper().replace('/', '-').replace(':', '-').replace('_', '-')
        if '-' in s and ('USDT' in s or 'SWAP' in s):
            return s
        if not s.endswith('USDT') and not s.endswith('SWAP'):
            s += '-USDT'
        if mode == 'future' and not s.endswith('SWAP'):
            s += '-SWAP'
        return s

    def get_ctval_info(self, symbol: str) -> Dict[str, Any]:
        """查询合约面值信息"""
        inst_id = self.format_symbol(symbol, 'future')
        # 获取合约产品信息
        res = self._public_api.get_instruments(instType='SWAP', instId=inst_id)
        if res['code'] != '0' or not res['data']:
            raise Exception(f"未找到合约: {inst_id}")
        ct_val = float(res['data'][0].get('ctVal', 0))
        # 获取当前标记价格
        ticker = self._market_api.get_ticker(instId=inst_id)
        if ticker['code'] != '0':
            mark_price = 0
        else:
            mark_price = float(ticker['data'][0].get('markPx', 0) or ticker['data'][0].get('last', 0))
        return {
            'inst_id': inst_id,
            'ct_val': ct_val,
            'mark_price': mark_price,
            'face_value': ct_val * mark_price if mark_price > 0 else 0,
        }

    def close_position(self, symbol: str, mode: str, margin_mode: str) -> Dict[str, Any]:
        """平仓 — 使用 OKX 原生 close_positions API，自动处理双向/单向持仓"""
        inst_id = self.format_symbol(symbol, 'future')
        pos_mode = self._posside_detector._get_pos_mode()
        if pos_mode == 'long_short_mode':
            # 双向持仓模式：逐个平仓 long 和 short
            results = []
            for ps in ['long', 'short']:
                res = self._trade_api.close_positions(instId=inst_id, mgnMode=margin_mode, posSide=ps)
                if res['code'] == '0':
                    results.append(res)
            if results:
                return {'code': '0', 'status': 'success', 'count': len(results)}
            return {'code': '-1', 'msg': '平仓失败'}
        else:
            # 单向持仓模式：不需要 posSide
            res = self._trade_api.close_positions(instId=inst_id, mgnMode=margin_mode)
            if res['code'] != '0':
                raise Exception(f"平仓失败: {res.get('msg', '')}")
            return {'code': '0', 'status': 'success'}

    def set_leverage(self, symbol: str, leverage: int, margin_mode: str) -> Dict[str, Any]:
        """设置合约杠杆和保证金模式"""
        inst_id = self.format_symbol(symbol, 'future')
        pos_side = self._posside_detector._get_pos_mode()
        kwargs: Dict[str, Any] = {'instId': inst_id, 'lever': str(leverage), 'mgnMode': margin_mode}
        if pos_side == 'long_short_mode':
            kwargs['posSide'] = 'long'
            self._adapter.set_leverage(**kwargs)
            kwargs['posSide'] = 'short'
        res = self._adapter.set_leverage(**kwargs)
        if res['code'] != '0':
            raise Exception(f"OKX 设置杠杆失败: {res.get('msg', '未知错误')}")
        return {'symbol': inst_id, 'leverage': leverage, 'margin_mode': margin_mode}
