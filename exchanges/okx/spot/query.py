"""OKX 现货查询功能：价格、余额、持仓、历史、挂单"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


class OKXSpotQueryMixin:
    """OKX 现货查询功能混入类"""

    def get_price_spot(self, symbol: str) -> float:
        """获取现货最新价格"""
        inst_id = self.format_symbol(symbol, 'spot')
        res = self._market_api.get_ticker(instId=inst_id)
        if res['code'] != '0':
            raise Exception(res['msg'])
        return float(res['data'][0]['last'])

    def get_balance_spot(self) -> Dict[str, Any]:
        """获取现货账户余额并标准化输出"""
        res = self._account_api.get_account_balance()
        if res['code'] != '0':
            raise Exception(res['msg'])
        balance: Dict[str, Any] = {'total': {}, 'free': {}, 'used': {}, 'info': res}
        for item in res['data'][0]['details']:
            ccy = item['ccy']
            balance['total'][ccy] = float(item['eq'])
            balance['free'][ccy] = float(item['availBal'])
            balance['used'][ccy] = float(item['frozenBal'])
        return balance

    def get_positions_spot(self) -> List[Dict[str, Any]]:
        """获取现货持仓（过滤衍生品），含可用/冻结拆分"""
        res = self._account_api.get_positions()
        # 取余额用于填充可用/冻结字段
        bal_free: Dict[str, float] = {}
        bal_locked: Dict[str, float] = {}
        try:
            bal_res = self._account_api.get_account_balance()
            if bal_res['code'] == '0':
                for item in bal_res['data'][0]['details']:
                    bal_free[item['ccy']] = float(item['availBal'])
                    bal_locked[item['ccy']] = float(item['frozenBal'])
        except Exception:
            pass

        positions: List[Dict[str, Any]] = []
        if res['code'] == '0':
            for pos in res['data']:
                inst_id = pos.get('instId', '')
                is_contract = 'SWAP' in inst_id or 'PERP' in inst_id
                if is_contract:
                    continue
                amt = float(pos.get('pos', 0))
                if amt != 0:
                    ccy = pos.get('ccy', inst_id.split('-')[0] if '-' in inst_id else inst_id)
                    side = pos.get('posSide', '').upper()
                    is_long = side in ['LONG', 'BUY'] or (side == 'NET' and amt > 0)
                    positions.append({
                        'symbol': inst_id,
                        'display_symbol': inst_id,
                        'contracts': abs(amt),
                        'free_balance': bal_free.get(ccy, abs(amt)),
                        'locked_balance': bal_locked.get(ccy, 0),
                        'side': side,
                        'is_long': is_long,
                        'entry_price': float(pos.get('avgPx', 0)),
                        'unrealized_pnl': float(pos.get('upl', 0)),
                        'leverage': float(pos.get('lever', 1)),
                        'margin_mode': pos.get('mgnMode', ''),
                        'notional': float(pos.get('notionalUsd', 0)),
                        'unit': '个'
                    })
        return positions

    def get_open_orders_spot(self, symbol: Optional[str]) -> List[Dict[str, Any]]:
        """获取现货挂单并统一清洗格式输出"""
        raw_orders: List[Dict[str, Any]] = []

        try:
            res_normal = self._trade_api.get_order_list(
                instType='SPOT')
            logger.info(f"OKX spot orders-pending: code={res_normal['code']} count={len(res_normal.get('data',[]))}")
            if res_normal['code'] == '0':
                raw_orders.extend(res_normal['data'])
            else:
                logger.warning(f"OKX 现货普通挂单查询失败: code={res_normal['code']} msg={res_normal.get('msg')}")
            for at in ['conditional', 'oco', 'move_order_stop']:
                res_algo = self._trade_api.order_algos_list(
                    instType='SPOT', ordType=at)
                if res_algo['code'] == '0':
                    raw_orders.extend(res_algo['data'])
                else:
                    logger.warning(f"OKX 现货策略单({at})查询失败: code={res_algo['code']} msg={res_algo.get('msg')}")
        except Exception as e:
            logger.error(f"OKX 获取现货挂单异常: {e}")
            raise Exception(f"网络异常或 API 超时，请稍后重试: {str(e)}")

        standardized: List[Dict[str, Any]] = []
        for o in raw_orders:
            sym = o.get('instId', '')

            # 时间处理 (强制 UTC+8)
            t = o.get('cTime') or o.get('uTime') or 0
            time_str = "未知"
            if t and float(t) > 1000000000:
                t_sec = float(t) / 1000 if float(t) > 1000000000000 else float(t)
                time_str = (datetime.fromtimestamp(t_sec, timezone.utc)
                            + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')

            # 触发参数合并
            trigger_info = ""
            tp_px = o.get('tpTriggerPx')
            sl_px = o.get('slTriggerPx')
            stop_px = o.get('slTriggerPx') or o.get('tpTriggerPx') or o.get('triggerPx')

            if tp_px and sl_px:
                trigger_info = f"止盈: {tp_px} | 止损: {sl_px}"
            elif tp_px:
                trigger_info = f"止盈: {tp_px}"
            elif sl_px:
                trigger_info = f"止损: {sl_px}"
            elif stop_px and float(stop_px) > 0:
                trigger_info = f"触发价: {stop_px}"

            # 回调比例过滤 None 和空字符串
            cb_ratio = o.get('callbackRatio')
            cb_str = ""
            if cb_ratio not in [None, ""]:
                cb_str = f"{float(cb_ratio) * 100}%"

            standardized.append({
                'id': str(o.get('algoId') or o.get('ordId') or ''),
                'symbol': sym,
                'display_symbol': sym,
                'type': str(o.get('ordType') or 'MARKET').upper(),
                'side': str(o.get('side') or o.get('posSide') or '').upper(),
                'amount': float(o.get('sz') or 0),
                'price': float(o.get('px') or 0),
                'status': str(o.get('state') or '').upper(),
                'trigger_info': trigger_info,
                'callback_str': cb_str,
                'active_px': o.get('activePx', ''),
                'time_str': time_str,
                'unit': '个',
                'raw': o
            })
        return standardized
