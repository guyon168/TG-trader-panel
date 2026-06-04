"""Binance 现货查询功能：价格、余额、持仓、历史、挂单"""
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


class BinanceSpotQueryMixin:
    """Binance 现货查询功能混入类"""

    def get_price_spot(self, symbol: str) -> float:
        """获取现货最新价格"""
        raw_s = self.format_symbol(symbol, 'spot')
        ticker = self.client.get_symbol_ticker(symbol=raw_s)
        return float(ticker['price'])

    def get_balance_spot(self) -> Dict[str, Any]:
        """获取现货账户余额"""
        res = self.client.get_account()
        balance: Dict[str, Any] = {'total': {}, 'free': {}, 'used': {}, 'info': res}
        for item in res['balances']:
            ccy = item['asset']
            free = float(item['free'])
            used = float(item['locked'])
            total = free + used
            if total > 0:
                balance['total'][ccy] = total
                balance['free'][ccy] = free
                balance['used'][ccy] = used
        return balance

    def get_positions_spot(self) -> List[Dict[str, Any]]:
        """获取现货持仓列表（含可用/冻结拆分）"""
        positions: List[Dict[str, Any]] = []
        res = self.client.get_account()
        for item in res.get('balances', []):
            free = float(item.get('free', 0))
            locked = float(item.get('locked', 0))
            if free > 0 or locked > 0:
                positions.append({
                    'symbol': item.get('asset'),
                    'display_symbol': item.get('asset'),
                    'contracts': free + locked,
                    'free_balance': free,
                    'locked_balance': locked,
                    'side': 'NET',
                    'is_long': True,
                    'entry_price': 0.0,
                    'unrealized_pnl': 0.0,
                    'leverage': 1.0,
                    'margin_mode': 'cash',
                    'notional': 0.0,
                    'unit': '个'
                })
        return positions

    def get_open_orders_spot(self, symbol: Optional[str]) -> List[Dict[str, Any]]:
        """获取现货挂单并统一清洗格式输出"""
        raw_s = self.format_symbol(symbol, 'spot') if symbol else None
        raw_orders: List[Dict[str, Any]] = []

        try:
            raw_orders = self.client.get_open_orders(symbol=raw_s)
        except Exception as e:
            logger.error(f"Binance 获取现货挂单失败: {str(e)}")

        standardized: List[Dict[str, Any]] = []
        for o in raw_orders:
            sym = o.get('symbol', '')
            disp_sym = sym

            t = o.get('time') or o.get('updateTime') or 0
            time_str = "未知"
            if t and float(t) > 1000000000:
                t_sec = float(t) / 1000 if float(t) > 1000000000000 else float(t)
                time_str = (datetime.fromtimestamp(t_sec, timezone.utc)
                            + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')

            trigger_info = ""
            stop_px = o.get('stopPrice') or o.get('triggerPrice')
            if stop_px and float(stop_px) > 0:
                trigger_info = f"触发价: {stop_px}"

            cb_str = ""
            tr_delta = o.get('trailingDelta')
            if tr_delta not in [None, ""]:
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
                'status': str(o.get('status') or '').upper(),
                'trigger_info': trigger_info,
                'callback_str': cb_str,
                'active_px': o.get('activationPrice', ''),
                'time_str': time_str,
                'unit': '个',
                'raw': o
            })
        return standardized
