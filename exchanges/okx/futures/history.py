"""OKX 合约历史仓位查询"""
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# type 字段映射 — positions-history 只记录已平仓仓位，不含"开仓"
_TYPE_MAP = {'2': '平仓', '3': '强平', '4': '自动减仓'}


class OKXFuturesHistoryMixin:
    """OKX U本位永续合约历史仓位查询"""

    def get_positions_history_futures(self, symbol: Optional[str]) -> List[Dict[str, Any]]:
        """获取合约历史仓位记录"""
        inst_id = self.format_symbol(symbol, 'future') if symbol else None
        res = self._account_api.get_positions_history(
            instId=inst_id, instType='SWAP', limit='20')
        history: List[Dict[str, Any]] = []
        if res['code'] == '0':
            for pos in res['data']:
                pos_side = pos.get('posSide', '').lower()
                pos_type = str(pos.get('type', ''))
                pnl = float(pos.get('pnl', 0))
                open_price = float(pos.get('openAvgPx', 0))
                close_price = float(pos.get('closeAvgPx', 0))

                # 方向: hedge 模式直接用 posSide
                # net 模式: (open < close) == (pnl >= 0) → 多单, 否则空单
                if pos_side == 'long':
                    direction = 'LONG'
                elif pos_side == 'short':
                    direction = 'SHORT'
                else:
                    direction = 'LONG' if (open_price < close_price) == (pnl >= 0) else 'SHORT'

                t_open = int(pos.get('cTime', 0))
                t_close = int(pos.get('uTime', 0))

                history.append({
                    'symbol': pos.get('instId'),
                    'display_symbol': pos.get('instId'),
                    'side': direction,
                    'openAvgPx': open_price,
                    'closeAvgPx': close_price,
                    'pnl': pnl,
                    'pnlRatio': float(pos.get('pnlRatio', 0)) * 100,
                    'sz': float(pos.get('closeTotalPos') or pos.get('openMaxPos') or 0),
                    'mgnMode': pos.get('mgnMode', 'N/A'),
                    'openTime': t_open,
                    'closeTime': t_close,
                    'unit': '张',
                    'type_label': _TYPE_MAP.get(pos_type, pos_type),
                })
        return history
