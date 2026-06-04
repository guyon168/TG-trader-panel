"""Binance 合约历史成交查询"""
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class BinanceFuturesHistoryMixin:
    """Binance U本位永续合约历史成交查询"""

    def get_positions_history_futures(self, symbol: Optional[str]) -> List[Dict[str, Any]]:
        """获取合约逐笔成交记录

        symbol 未指定：查最近全部成交
        symbol 指定：只查该币对的成交
        """
        raw_s = self.format_symbol(symbol, 'future') if symbol else None
        fills = self.client.futures_account_trades(symbol=raw_s, limit=30)
        margin_mode = getattr(self, 'margin_mode', 'isolated')

        history: List[Dict[str, Any]] = []
        for f in fills:
            sym = f.get('symbol')
            history.append({
                'symbol': sym,
                'display_symbol': f"{sym}-PERP" if 'PERP' not in sym else sym,
                'side': f.get('side'),
                'openAvgPx': float(f.get('price', 0)),
                'pnl': float(f.get('realizedPnl', 0)),
                'sz': float(f.get('qty', 0)),
                'mgnMode': margin_mode,
                'openTime': f.get('time', 0),
                'unit': '个',
            })
        history.reverse()
        return history
