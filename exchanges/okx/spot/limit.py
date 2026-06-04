"""OKX 现货限价单 — 修复 BUG-3 (现货限价单缺 tgtCcy)"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class OKXSpotLimitMixin:
    """OKX 现货限价单功能混入类"""

    def place_limit_order_spot(self, symbol: str, side: str, amount: float,
                               price: float, is_usdt: bool) -> Dict[str, Any]:
        """现货限价单 (解决 USDT 与个数的自动换算)

        BUG-3 修复: 现货限价单统一传入 tgtCcy
        """
        inst_id = self.format_symbol(symbol, 'spot')
        sz = amount
        unit_str = '个'
        # BUG-3 修复: 现货限价单也传入 tgtCcy
        kwargs = {'px': str(price), 'tgtCcy': 'quote_ccy' if is_usdt else 'base_ccy'}
        if is_usdt:
            sz = round(amount / price, 4)

        res = self._trade_api.place_order(
            inst_id, 'cash', side.lower(), 'limit', str(sz), **kwargs)
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
