"""Binance 合约止盈止损"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class BinanceFuturesTpslMixin:
    """Binance U本位永续合约止盈止损功能混入类"""

    def place_tp_futures(self, symbol: str, side: str, amount: float,
                         tp_price: float, reduce_only: bool = False) -> Dict[str, Any]:
        """合约设置止盈单"""
        raw_s = self.format_symbol(symbol, 'future')
        res = self.client._request_futures_api(
            'post', 'algoOrder', signed=True,
            data={
                'algoType': 'CONDITIONAL',
                'symbol': raw_s,
                'side': side.upper(),
                'type': 'TAKE_PROFIT_MARKET',
                'quantity': str(amount),
                'triggerPrice': str(tp_price),
                'reduceOnly': 'true' if reduce_only else 'false'
            })
        if 'algoId' in res:
            res['orderId'] = res['algoId']
        return res

    def place_sl_futures(self, symbol: str, side: str, amount: float,
                         sl_price: float, reduce_only: bool = False) -> Dict[str, Any]:
        """合约设置止损单"""
        raw_s = self.format_symbol(symbol, 'future')
        res = self.client._request_futures_api(
            'post', 'algoOrder', signed=True,
            data={
                'algoType': 'CONDITIONAL',
                'symbol': raw_s,
                'side': side.upper(),
                'type': 'STOP_MARKET',
                'quantity': str(amount),
                'triggerPrice': str(sl_price),
                'reduceOnly': 'true' if reduce_only else 'false'
            })
        if 'algoId' in res:
            res['orderId'] = res['algoId']
        return res

    def place_tpsl_futures(self, symbol: str, side: str, amount: float,
                           tp: Optional[float], sl: Optional[float],
                           reduce_only: bool = False) -> Dict[str, Any]:
        """合约止盈止损条件单路由"""
        raw_s = self.format_symbol(symbol, 'future')
        side_up = side.upper()
        res_dict: Dict[str, Any] = {}

        if tp:
            res_dict['tp'] = self.place_tp_futures(raw_s, side_up, amount, tp, reduce_only)
        if sl:
            res_dict['sl'] = self.place_sl_futures(raw_s, side_up, amount, sl, reduce_only)

        return res_dict
