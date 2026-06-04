"""OKX 现货止盈止损"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class OKXSpotTpslMixin:
    """OKX 现货止盈止损功能混入类"""

    def place_tpsl_spot(self, symbol: str, side: str, amount: float,
                        tp: Optional[float], sl: Optional[float]) -> Dict[str, Any]:
        """现货止盈止损条件单 (支持双向或单向)"""
        inst_id = self.format_symbol(symbol, 'spot')
        params: Dict[str, Any] = {
            'instId': inst_id,
            'tdMode': 'cash',
            'side': side.lower(),
            'ordType': 'oco' if tp and sl else 'conditional',
            'sz': str(amount)
        }

        if tp:
            params.update({'tpTriggerPx': str(tp), 'tpOrdPx': '-1'})
        if sl:
            params.update({'slTriggerPx': str(sl), 'slOrdPx': '-1'})

        res = self._trade_api.place_algo_order(**params)
        if res['code'] != '0':
            raise Exception(
                f"{res.get('msg', '')} {res['data'][0].get('sMsg', '') if res.get('data') else ''}")
        return {'status': 'success'}
