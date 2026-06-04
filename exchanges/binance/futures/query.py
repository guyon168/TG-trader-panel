"""Binance 合约查询功能：价格、余额、持仓、历史、挂单"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


class BinanceFuturesQueryMixin:
    """Binance U本位永续合约查询功能混入类"""

    def get_price_futures(self, symbol: str) -> float:
        """获取合约最新价格"""
        raw_s = self.format_symbol(symbol, 'future')
        ticker = self.client.futures_symbol_ticker(symbol=raw_s)
        return float(ticker['price'])

    def get_balance_futures(self) -> Dict[str, Any]:
        """获取合约账户余额"""
        res = self.client.futures_account_balance()
        balance: Dict[str, Any] = {'total': {}, 'free': {}, 'used': {}, 'info': res}
        for item in res:
            ccy = item['asset']
            total = float(item.get('balance', 0))
            free = float(item.get('availableBalance', 0))
            used = total - free
            if total > 0:
                balance['total'][ccy] = total
                balance['free'][ccy] = free
                balance['used'][ccy] = used
        return balance

    def get_positions_futures(self) -> List[Dict[str, Any]]:
        """获取合约持仓列表"""
        positions: List[Dict[str, Any]] = []
        res = self.client.futures_account()
        for pos in res.get('positions', []):
            amt = float(pos.get('positionAmt', 0))
            if amt != 0:
                sym = pos.get('symbol')
                side = 'LONG' if amt > 0 else 'SHORT'
                positions.append({
                    'symbol': sym,
                    'display_symbol': f"{sym}-PERP",
                    'contracts': abs(amt),
                    'side': side,
                    'is_long': side == 'LONG',
                    'entry_price': float(pos.get('entryPrice', 0)),
                    'unrealized_pnl': float(pos.get('unrealizedProfit', 0)),
                    'leverage': float(pos.get('leverage', 1)),
                    'margin_mode': 'isolated' if pos.get('isolated') else 'cross',
                    'notional': float(pos.get('notional', 0)),
                    'unit': '个'
                })
        return positions

    def get_open_orders_futures(self, symbol: Optional[str]) -> List[Dict[str, Any]]:
        """获取合约挂单并统一清洗格式输出"""
        raw_s = self.format_symbol(symbol, 'future') if symbol else None
        raw_orders: List[Dict[str, Any]] = []

        try:
            try:
                raw_orders.extend(self.client.futures_get_open_orders(symbol=raw_s))
            except Exception:
                pass

            try:
                algo_res = self.client._request_futures_api(
                    'get', 'openAlgoOrders', signed=True,
                    data={'symbol': raw_s} if raw_s else {})
                algo_list = (algo_res if isinstance(algo_res, list)
                             else (algo_res.get('orders') or algo_res.get('data') or []))
                for ao in algo_list:
                    if (ao.get('algoStatus') in ['WORKING', 'NEW']
                            or ao.get('status') in ['WORKING', 'NEW']):
                        ao['is_algo'] = True
                        raw_orders.append(ao)
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Binance 获取合约挂单失败: {str(e)}")

        standardized: List[Dict[str, Any]] = []
        for o in raw_orders:
            sym = o.get('symbol', '')
            disp_sym = f"{sym}-PERP" if 'PERP' not in sym else sym

            t = o.get('time') or o.get('updateTime') or 0
            time_str = "未知"
            if t and float(t) > 1000000000:
                t_sec = float(t) / 1000 if float(t) > 1000000000000 else float(t)
                time_str = (datetime.fromtimestamp(t_sec, timezone.utc)
                            + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')

            trigger_info = ""
            tp_px = o.get('tpTriggerPx')
            sl_px = o.get('slTriggerPx')
            stop_px = o.get('stopPrice') or o.get('triggerPrice')
            if tp_px and sl_px:
                trigger_info = f"止盈: {tp_px} | 止损: {sl_px}"
            elif tp_px:
                trigger_info = f"止盈: {tp_px}"
            elif sl_px:
                trigger_info = f"止损: {sl_px}"
            elif stop_px and float(stop_px) > 0:
                trigger_info = f"触发价: {stop_px}"

            cb_rate = o.get('callbackRate')
            tr_delta = o.get('trailingDelta')
            cb_str = ""
            if cb_rate not in [None, ""]:
                cb_str = f"{cb_rate}%"
            elif tr_delta not in [None, ""]:
                cb_str = f"{float(tr_delta) / 100}%"

            real_type = str(o.get('type') or o.get('orderType')
                            or o.get('algoType') or 'MARKET').upper()

            standardized.append({
                'id': str(o.get('orderId') or o.get('algoId') or ''),
                'symbol': sym,
                'display_symbol': disp_sym,
                'type': real_type,
                'side': str(o.get('side', '')).upper(),
                'amount': float(o.get('origQty') or o.get('quantity') or 0),
                'price': float(o.get('price') or 0),
                'status': str(o.get('status') or o.get('algoStatus') or '').upper(),
                'trigger_info': trigger_info,
                'callback_str': cb_str,
                'active_px': o.get('activationPrice', ''),
                'time_str': time_str,
                'unit': '个',
                'raw': o
            })
        return standardized
