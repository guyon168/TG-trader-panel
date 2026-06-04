"""OKX 合约止盈止损 — 修复 BUG-1 (posSide 动态检测)"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class OKXFuturesTpslMixin:
    """OKX 合约止盈止损功能混入类"""

    def place_tpsl_futures(self, symbol: str, side: str, amount: float,
                           tp: Optional[float], sl: Optional[float],
                           margin_mode: str, reduce_only: bool = False) -> Dict[str, Any]:
        """合约止盈止损条件单"""
        inst_id = self.format_symbol(symbol, 'future')
        params: Dict[str, Any] = {
            'instId': inst_id,
            'tdMode': margin_mode,
            'side': side.lower(),
            'ordType': 'oco' if tp and sl else 'conditional',
            'sz': str(amount),
            'reduceOnly': 'true' if reduce_only else 'false',
        }

        # BUG-1 修复: 动态获取 posSide
        pos_side = self._posside_detector.get_pos_side(inst_id, 'future', side)
        if pos_side:
            params['posSide'] = pos_side

        if tp:
            params.update({'tpTriggerPx': str(tp), 'tpOrdPx': '-1'})
        if sl:
            params.update({'slTriggerPx': str(sl), 'slOrdPx': '-1'})

        res = self._trade_api.place_algo_order(**params)
        if res['code'] != '0':
            raise Exception(
                f"{res.get('msg', '')} {res['data'][0].get('sMsg', '') if res.get('data') else ''}")
        return {'status': 'success'}
