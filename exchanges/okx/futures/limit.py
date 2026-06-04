"""OKX 合约限价单 — 修复 BUG-1 (posSide), BUG-2 (ctVal)"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class OKXFuturesLimitMixin:
    """OKX 合约限价单功能混入类"""

    def place_limit_order_futures(self, symbol: str, side: str, amount: float,
                                  price: float, is_usdt: bool, leverage: int,
                                  margin_mode: str) -> Dict[str, Any]:
        """合约限价单 (解决 USDT 与张数的自动换算)

        BUG-1 修复: 使用 posside_detector 获取 posSide
        BUG-2 修复: 使用 ctval_cache 获取 ctVal
        """
        inst_id = self.format_symbol(symbol, 'future')
        sz = amount
        unit_str = '张'

        # BUG-1 修复: 动态获取 posSide
        pos_side = self._posside_detector.get_pos_side(inst_id, 'future', side)
        kwargs: Dict[str, Any] = {'px': str(price)}
        if pos_side:
            kwargs['posSide'] = pos_side
        if is_usdt:
            # BUG-2 修复: 使用 ctval_cache 获取 ctVal
            cv = self._ctval_cache.get_ctval(inst_id)
            sz = max(1, int((amount * leverage) / (price * cv)))

        res = self._trade_api.place_order(
            inst_id, margin_mode, side.lower(), 'limit', str(sz), **kwargs)
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
