"""OKX 现货历史成交查询"""
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class OKXSpotHistoryMixin:
    """OKX 现货历史成交查询"""

    def get_positions_history_spot(self, symbol: Optional[str]) -> List[Dict[str, Any]]:
        """获取现货成交记录（OKX 现货无"仓位"概念，用成交明细替代）"""
        inst_id = self.format_symbol(symbol, 'spot') if symbol else None
        kwargs: Dict[str, Any] = {'instType': 'SPOT', 'limit': '30'}
        if inst_id:
            kwargs['instId'] = inst_id
        res = self._trade_api.get_fills_history(**kwargs)
        if res['code'] != '0':
            logger.warning(f"OKX spot fills-history: code={res['code']} msg={res.get('msg')}")
            return []

        history: List[Dict[str, Any]] = []
        for f in res.get('data', []):
            history.append({
                'symbol': f.get('instId'),
                'display_symbol': f.get('instId'),
                'side': f.get('side'),
                'openAvgPx': float(f.get('fillPx', 0)),
                'pnl': float(f.get('fillPnl', 0)),
                'sz': float(f.get('fillSz', 0)),
                'mgnMode': 'SPOT',
                'openTime': int(f.get('ts', 0)),
                'unit': '个',
            })
        return history
