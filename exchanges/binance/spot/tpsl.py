"""Binance 现货止盈止损"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class BinanceSpotTpslMixin:
    """Binance 现货止盈止损功能混入类"""

    def place_tp_spot(self, symbol: str, side: str, amount: float,
                      tp_price: float) -> Dict[str, Any]:
        """现货设置止盈单"""
        raw_s = self.format_symbol(symbol, 'spot')
        side_up = side.upper()
        return self.client.create_order(
            symbol=raw_s, side=side_up, type='LIMIT',
            price=tp_price, quantity=amount, timeInForce='GTC')

    def place_sl_spot(self, symbol: str, side: str, amount: float,
                      sl_price: float) -> Dict[str, Any]:
        """现货设置止损单"""
        raw_s = self.format_symbol(symbol, 'spot')
        side_up = side.upper()
        return self.client.create_order(
            symbol=raw_s, side=side_up, type='STOP_LOSS_LIMIT',
            stopPrice=sl_price, price=sl_price, quantity=amount,
            timeInForce='GTC')

    def place_tpsl_spot(self, symbol: str, side: str, amount: float,
                        tp: Optional[float], sl: Optional[float]) -> Dict[str, Any]:
        """现货止盈止损条件单路由（支持双向或单向）"""
        raw_s = self.format_symbol(symbol, 'spot')
        side_up = side.upper()
        res_dict: Dict[str, Any] = {}

        if tp and sl:
            try:
                params = {'symbol': raw_s, 'side': side_up, 'quantity': amount}
                if side_up == 'SELL':
                    params['aboveType'] = 'LIMIT_MAKER'
                    params['abovePrice'] = str(tp)
                    params['belowType'] = 'STOP_LOSS_LIMIT'
                    params['belowStopPrice'] = str(sl)
                    params['belowPrice'] = str(sl)
                    params['belowTimeInForce'] = 'GTC'
                else:
                    params['belowType'] = 'LIMIT_MAKER'
                    params['belowPrice'] = str(tp)
                    params['aboveType'] = 'STOP_LOSS_LIMIT'
                    params['aboveStopPrice'] = str(sl)
                    params['abovePrice'] = str(sl)
                    params['aboveTimeInForce'] = 'GTC'

                res_dict['oco'] = self.client.create_oco_order(**params)
            except Exception as e:
                if "insufficient balance" in str(e).lower():
                    raise Exception("账户可用余额不足 (Insufficient balance)")
                elif "aboveType" in str(e) or "code=-1102" in str(e):
                    logger.warning(f"Binance 尝试旧版 OCO: {str(e)}")
                    try:
                        res_dict['oco'] = self.client.create_oco_order(
                            symbol=raw_s, side=side_up, quantity=amount,
                            price=str(tp), stopPrice=str(sl),
                            stopLimitPrice=str(sl), stopLimitTimeInForce='GTC')
                    except Exception as old_e:
                        if "insufficient balance" in str(old_e).lower():
                            raise Exception("账户可用余额不足 (Insufficient balance)")
                        raise old_e
                else:
                    raise e
        elif tp:
            res_dict['tp'] = self.place_tp_spot(raw_s, side_up, amount, tp)
        elif sl:
            res_dict['sl'] = self.place_sl_spot(raw_s, side_up, amount, sl)

        return res_dict
