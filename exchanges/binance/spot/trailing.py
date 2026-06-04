"""Binance 现货移动止损 — 修复 BUG-5: trailing stop 类型判断逻辑"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class BinanceSpotTrailingMixin:
    """Binance 现货移动止损功能混入类"""

    def place_trailing_stop_spot(self, symbol: str, side: str, amount: float,
                                 callback_ratio: float, active_px: Optional[float],
                                 is_usdt: bool) -> Dict[str, Any]:
        """现货移动止损

        Binance 现货 trailing stop 的类型取决于买卖方向 **和** 激活价与当前价的关系：
        - BUY:  active_px < 当前价 → TAKE_PROFIT（下跌接多）; active_px > 当前价 → STOP_LOSS（上涨追多）
        - SELL: active_px < 当前价 → STOP_LOSS（下跌止损）; active_px > 当前价 → TAKE_PROFIT（上涨止盈）
        """
        raw_s = self.format_symbol(symbol, 'spot')
        side_up = side.upper()
        # 始终取真实市价，不以 active_px 作 fallback
        current_price = self.get_price_spot(raw_s)
        qty = (self.calculate_quantity(raw_s, amount, current_price, 'spot')
               if is_usdt else amount)

        bips = int(callback_ratio * 10000)
        # 综合方向 + stop 位置确定类型
        if active_px and float(active_px) < current_price:
            order_type = 'TAKE_PROFIT' if side_up == 'BUY' else 'STOP_LOSS'
        elif active_px and float(active_px) > current_price:
            order_type = 'STOP_LOSS' if side_up == 'BUY' else 'TAKE_PROFIT'
        else:
            order_type = 'STOP_LOSS'  # 无 px 或 px≈市价时默认

        params: Dict[str, Any] = {
            'symbol': raw_s,
            'side': side_up,
            'type': order_type,
            'quantity': qty,
            'trailingDelta': bips
        }
        if active_px:
            params['stopPrice'] = str(active_px)
        res = self.client.create_order(**params)
        return {'id': res.get('orderId'), 'symbol': raw_s, 'amount': qty, 'unit': '个'}
