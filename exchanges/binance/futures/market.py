"""Binance 合约市价单"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class BinanceFuturesMarketMixin:
    """Binance U本位永续合约市价单功能混入类"""

    def place_market_order_futures(self, symbol: str, side: str, amount: float,
                                   is_usdt: bool, leverage: int,
                                   margin_mode: str) -> Dict[str, Any]:
        """合约市价下单"""
        raw_s = self.format_symbol(symbol, 'future')
        side_up = side.upper()
        self.set_leverage_and_margin(raw_s, leverage, margin_mode)
        qty = amount
        if is_usdt:
            p = self.get_price_futures(raw_s)
            qty = self.calculate_quantity(raw_s, amount * leverage, p, 'future')
        res = self.client.futures_create_order(
            symbol=raw_s, side=side_up, type='MARKET', quantity=qty)
        executed = float(res.get('executedQty', 0))
        return {
            'id': res.get('orderId'),
            'symbol': raw_s,
            'side': side_up,
            'amount': executed if executed > 0 else qty,
            'unit': '个'
        }
