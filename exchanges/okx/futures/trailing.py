"""OKX 合约移动止损 — 修复 BUG-1 (posSide), BUG-2 (ctVal)"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class OKXFuturesTrailingMixin:
    """OKX 合约移动止损功能混入类"""

    def place_trailing_stop_futures(self, symbol: str, side: str, amount: float,
                                    callback_ratio: float, active_px: Optional[float],
                                    is_usdt: bool, leverage: int,
                                    margin_mode: str, reduce_only: bool = False) -> Dict[str, Any]:
        """合约移动追踪止损"""
        inst_id = self.format_symbol(symbol, 'future')
        sz = amount
        unit_str = '张'

        if is_usdt:
            calc_price = active_px if active_px else self.get_price_futures(symbol)
            cv = self._ctval_cache.get_ctval(inst_id)
            sz = max(1, int((amount * leverage) / (calc_price * cv)))

        params: Dict[str, Any] = {
            'instId': inst_id,
            'tdMode': margin_mode,
            'side': side.lower(),
            'ordType': 'move_order_stop',
            'sz': str(sz),
            'callbackRatio': str(callback_ratio),
            'reduceOnly': 'true' if reduce_only else 'false',
        }

        pos_side = self._posside_detector.get_pos_side(inst_id, 'future', side)
        if pos_side:
            params['posSide'] = pos_side

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
