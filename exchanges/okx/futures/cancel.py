"""OKX 合约撤单功能 — 修复 BUG-4: 撤单 instId 可能为 None"""
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class OKXFuturesCancelMixin:
    """OKX 合约撤单功能混入类"""

    def cancel_orders_futures(self, symbol: Optional[str], order_id: Optional[str]) -> int:
        """撤单 (内部消化普通限价单和策略单的差异)

        BUG-4 修复: 当 instId 为 None 时，从挂单列表中获取对应 instId
        """
        inst_id = self.format_symbol(symbol, 'future') if symbol else None
        count = 0

        if order_id:
            # BUG-4 修复: 如果 inst_id 为 None，先从挂单列表查找
            if not inst_id:
                inst_id = self._find_inst_id_by_order_id_futures(order_id)

            # 先尝试撤销策略单
            algo_params: List[Dict[str, str]] = [{'algoId': order_id}]
            if inst_id:
                algo_params = [{'instId': inst_id, 'algoId': order_id}]
            res1 = self._trade_api.cancel_algo_order(algo_params)
            if res1['code'] == '0':
                count += 1
            else:
                # 再尝试撤销普通单
                if inst_id:
                    res2 = self._trade_api.cancel_order(instId=inst_id, ordId=order_id)
                else:
                    res2 = self._trade_api.cancel_order(ordId=order_id)
                if res2['code'] == '0':
                    count += 1
        else:
            open_orders = self.get_open_orders_futures(symbol)
            algo_list = [{'instId': o['symbol'], 'algoId': o['id']}
                         for o in open_orders if o['raw'].get('algoId')]
            normal_list = [{'instId': o['symbol'], 'ordId': o['id']}
                           for o in open_orders if o['raw'].get('ordId')]
            if algo_list:
                res = self._trade_api.cancel_algo_order(algo_list)
                if res['code'] == '0':
                    count += len(algo_list)
            if normal_list:
                res = self._trade_api.cancel_multiple_orders(normal_list)
                if res['code'] == '0':
                    count += len(normal_list)
        return count

    def _find_inst_id_by_order_id_futures(self, order_id: str) -> Optional[str]:
        """通过订单 ID 查找 instId (合约)"""
        try:
            res = self._trade_api.get_fills(ordId=order_id, instType='SWAP', limit='1')
            if res['code'] == '0' and res['data']:
                return res['data'][0].get('instId')
        except Exception:
            pass
        try:
            res = self._trade_api.get_algo_order_details(algoId=order_id)
            if res['code'] == '0' and res['data']:
                return res['data'][0].get('instId')
        except Exception:
            pass
        try:
            orders = self.get_open_orders_futures(None)
            for o in orders:
                if str(o.get('id')) == str(order_id):
                    return o.get('symbol')
        except Exception as e:
            logger.warning(f"OKX 通过订单ID查找instId失败: {str(e)}")
        return None
