"""OKX 现货市价单"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class OKXSpotMarketMixin:
    """OKX 现货市价单功能混入类"""

    def place_market_order_spot(self, symbol: str, side: str, amount: float,
                                is_usdt: bool) -> Dict[str, Any]:
        """现货市价单 (解决 USDT 与个数的自动换算)"""
        inst_id = self.format_symbol(symbol, 'spot')
        sz = amount

        # 现货明确告诉 OKX 下单数量是 U 还是 个
        kwargs = {'tgtCcy': 'quote_ccy' if is_usdt else 'base_ccy'}
        unit_str = 'USDT' if is_usdt else '个'

        res = self._trade_api.place_order(
            inst_id, 'cash', side.lower(), 'market', str(sz), **kwargs)
        if res['code'] != '0':
            raise Exception(
                f"{res.get('msg', '')} {res['data'][0].get('sMsg', '') if res.get('data') else ''}")

        return {
            'id': res['data'][0]['ordId'],
            'symbol': inst_id,
            'side': side.upper(),
            'amount': float(sz),
            'unit': unit_str
        }
