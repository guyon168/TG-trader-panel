"""OKX 现货移动止损"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class OKXSpotTrailingMixin:
    """OKX 现货移动止损功能混入类"""

    def place_trailing_stop_spot(self, symbol: str, side: str, amount: float,
                                 callback_ratio: float, active_px: Optional[float],
                                 is_usdt: bool) -> Dict[str, Any]:
        """现货移动追踪止损 (支持 USDT 自动换算)"""
        inst_id = self.format_symbol(symbol, 'spot')
        sz = amount
        unit_str = '个'

        if is_usdt:
            calc_price = active_px if active_px else self.get_price_spot(symbol)
            sz = round(amount / calc_price, 4)

        params: Dict[str, Any] = {
            'instId': inst_id,
            'tdMode': 'cash',
            'side': side.lower(),
            'ordType': 'move_order_stop',
            'sz': str(sz),
            'callbackRatio': str(callback_ratio)
        }

        if active_px:
            params['activePx'] = str(active_px)

        res = self._trade_api.place_algo_order(**params)
        if res['code'] != '0':
            raise Exception(
                f"{res.get('msg', '')} {res['data'][0].get('sMsg', '') if res.get('data') else ''}")
        return {
            'id': res['data'][0].get('algoId', '未知'),
            'symbol': inst_id,
            'amount': float(sz),
            'unit': unit_str
        }
