"""Binance 合约移动止损"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class BinanceFuturesTrailingMixin:
    """Binance U本位永续合约移动止损功能混入类"""

    def place_trailing_stop_futures(self, symbol: str, side: str, amount: float,
                                    callback_ratio: float, active_px: Optional[float],
                                    is_usdt: bool, leverage: int,
                                    reduce_only: bool = False) -> Dict[str, Any]:
        """合约移动止损"""
        raw_s = self.format_symbol(symbol, 'future')
        side_up = side.upper()
        current_price = self.get_price_futures(raw_s)
        qty = (self.calculate_quantity(raw_s, amount * leverage, current_price, 'future')
               if is_usdt else amount)

        params: Dict[str, Any] = {
            'algoType': 'CONDITIONAL',
            'symbol': raw_s,
            'side': side_up,
            'type': 'TRAILING_STOP_MARKET',
            'quantity': str(qty),
            'callbackRate': str(round(callback_ratio * 100, 1)),
            'reduceOnly': 'true' if reduce_only else 'false'
        }
        if active_px:
            params['activationPrice'] = str(active_px)
        res = self.client._request_futures_api('post', 'algoOrder', signed=True, data=params)
        return {'id': res.get('algoId'), 'symbol': raw_s, 'amount': qty, 'unit': '个'}
