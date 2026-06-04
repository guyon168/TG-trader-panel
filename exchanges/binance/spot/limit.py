"""Binance 现货限价单"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class BinanceSpotLimitMixin:
    """Binance 现货限价单功能混入类"""

    def place_limit_order_spot(self, symbol: str, side: str, amount: float,
                               price: float, is_usdt: bool) -> Dict[str, Any]:
        """现货限价下单"""
        raw_s = self.format_symbol(symbol, 'spot')
        side_up = side.upper()
        qty = amount
        if is_usdt:
            qty = self.calculate_quantity(raw_s, amount, price, 'spot')
        kwargs = {'quantity': qty, 'price': price, 'timeInForce': 'GTC'}
        res = self.client.create_order(
            symbol=raw_s, side=side_up, type='LIMIT', **kwargs)
        return {
            'id': res.get('orderId'),
            'symbol': raw_s,
            'side': side_up,
            'amount': qty,
            'unit': '个'
        }
