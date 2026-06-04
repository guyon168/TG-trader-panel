"""Binance 现货市价单"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class BinanceSpotMarketMixin:
    """Binance 现货市价单功能混入类"""

    def place_market_order_spot(self, symbol: str, side: str, amount: float,
                                is_usdt: bool) -> Dict[str, Any]:
        """现货市价下单"""
        raw_s = self.format_symbol(symbol, 'spot')
        side_up = side.upper()
        kwargs = {'quoteOrderQty': amount} if is_usdt else {'quantity': amount}
        res = self.client.create_order(
            symbol=raw_s, side=side_up, type='MARKET', **kwargs)
        executed = float(res.get('executedQty', 0))
        return {
            'id': res.get('orderId'),
            'symbol': raw_s,
            'side': side_up,
            'amount': executed if executed > 0 else amount,
            'unit': '个'
        }
