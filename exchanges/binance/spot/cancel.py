"""Binance 现货撤单功能"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class BinanceSpotCancelMixin:
    """Binance 现货撤单功能混入类"""

    def cancel_orders_spot(self, symbol: Optional[str], order_id: Optional[str]) -> int:
        """撤销现货订单，返回成功撤销数量"""
        count = 0
        raw_s = self.format_symbol(symbol, 'spot') if symbol else None

        try:
            if order_id:
                self.client.cancel_order(symbol=raw_s, orderId=order_id)
                count = 1
                return count

            open_orders = self.get_open_orders_spot(raw_s)
            if not open_orders:
                return 0

            for o in open_orders:
                try:
                    self.client.cancel_order(symbol=o['symbol'], orderId=o['id'])
                    count += 1
                except Exception as e:
                    if "code=-2011" not in str(e):
                        logger.warning(f"Binance 撤销现货订单失败: {e}")
            return count
        except Exception as e:
            logger.error(f"Binance 现货撤单异常: {str(e)}")
            raise
