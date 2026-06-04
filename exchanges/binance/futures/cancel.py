"""Binance 合约撤单功能"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class BinanceFuturesCancelMixin:
    """Binance U本位永续合约撤单功能混入类"""

    def cancel_orders_futures(self, symbol: Optional[str], order_id: Optional[str]) -> int:
        """撤销合约订单，返回成功撤销数量"""
        count = 0
        raw_s = self.format_symbol(symbol, 'future') if symbol else None

        try:
            if order_id:
                try:
                    self.client.futures_cancel_order(symbol=raw_s, orderId=order_id)
                    count = 1
                except Exception as e:
                    if ("Order was not found" in str(e)
                            or "code=-2011" in str(e)
                            or str(order_id).isdigit()):
                        self.client._request_futures_api(
                            'delete', 'algoOrder', signed=True,
                            data={'algoId': order_id, 'symbol': raw_s})
                        count = 1
                return count

            open_orders = self.get_open_orders_futures(raw_s)
            if not open_orders:
                return 0

            syms_to_cancel = set([o['symbol'] for o in open_orders])
            for s in syms_to_cancel:
                try:
                    self.client.futures_cancel_all_open_orders(symbol=s)
                except Exception:
                    pass
            for o in open_orders:
                if o.get('raw', {}).get('is_algo') or o.get('raw', {}).get('algoId'):
                    try:
                        self.client._request_futures_api(
                            'delete', 'algoOrder', signed=True,
                            data={'algoId': o['id'], 'symbol': o['symbol']})
                    except Exception:
                        pass
            count = len(open_orders)
            return count
        except Exception as e:
            logger.error(f"Binance 合约撤单异常: {str(e)}")
            raise
