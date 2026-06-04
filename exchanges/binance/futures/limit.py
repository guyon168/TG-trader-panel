"""Binance 合约限价单"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class BinanceFuturesLimitMixin:
    """Binance U本位永续合约限价单功能混入类"""

    def place_limit_order_futures(self, symbol: str, side: str, amount: float,
                                  price: float, is_usdt: bool, leverage: int,
                                  margin_mode: str) -> Dict[str, Any]:
        """合约限价下单"""
        raw_s = self.format_symbol(symbol, 'future')
        side_up = side.upper()
        self.set_leverage_and_margin(raw_s, leverage, margin_mode)
        qty = amount
        if is_usdt:
            qty = self.calculate_quantity(
                raw_s, amount * leverage, price, 'future')
        kwargs = {'quantity': qty, 'price': price, 'timeInForce': 'GTC'}
        res = self.client.futures_create_order(
            symbol=raw_s, side=side_up, type='LIMIT', **kwargs)
        return {
            'id': res.get('orderId'),
            'symbol': raw_s,
            'side': side_up,
            'amount': qty,
            'unit': '个'
        }
