"""OKX 合约面值缓存，启动时预加载，TTL 24h

修复 BUG-2: OKX ctVal 硬编码 → 通过 API 动态获取
"""
import logging
import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class CTValCache:
    """OKX 合约面值缓存

    原始代码中 ctVal 硬编码为:
        0.1 if 'ETH' in inst_id else 0.01 if BTC/BNB/SOL else 1

    本类改为启动时批量查询所有 SWAP 合约的 ctVal 并缓存，
    单个未命中时再实时查询，最终 fallback 返回 1.0。
    """

    DEFAULT_TTL = 86400  # 24 小时

    def __init__(self, adapter, ttl: int = DEFAULT_TTL):
        self._adapter = adapter
        self._cache: Dict[str, float] = {}
        self._last_refresh: float = 0
        self._ttl = ttl

    def get_ctval(self, inst_id: str) -> float:
        """获取合约面值，带缓存"""
        if self._is_cache_valid() and inst_id in self._cache:
            return self._cache[inst_id]

        # 缓存失效，尝试刷新
        if not self._is_cache_valid():
            self.refresh()

        # 刷新后再查一次
        if inst_id in self._cache:
            return self._cache[inst_id]

        # 单个查询兜底
        val = self._fetch_single(inst_id)
        if val is not None:
            self._cache[inst_id] = val
            return val

        # 最终 fallback
        logger.warning(f"CTValCache: 无法获取 {inst_id} 的 ctVal，使用默认值 1.0")
        return 1.0

    def refresh(self):
        """批量刷新所有 SWAP 合约的 ctVal 缓存"""
        try:
            res = self._adapter.get_instruments(instType='SWAP')
            if res.get('code') == '0' and res.get('data'):
                self._cache.clear()
                for inst in res['data']:
                    iid = inst.get('instId', '')
                    ctval = inst.get('ctVal')
                    if iid and ctval:
                        self._cache[iid] = float(ctval)
                self._last_refresh = time.time()
                logger.info(f"CTValCache: 已缓存 {len(self._cache)} 个合约面值")
            else:
                logger.warning(f"CTValCache: 批量刷新失败 - {res.get('msg', 'unknown')}")
        except Exception as e:
            logger.error(f"CTValCache: 批量刷新异常 - {str(e)}")

    def _fetch_single(self, inst_id: str) -> Optional[float]:
        """单个查询兜底"""
        try:
            res = self._adapter.get_instruments(instType='SWAP', instId=inst_id)
            if res.get('code') == '0' and res.get('data'):
                for inst in res['data']:
                    if inst.get('instId') == inst_id:
                        return float(inst.get('ctVal', 1.0))
        except Exception as e:
            logger.error(f"CTValCache: 单个查询 {inst_id} 异常 - {str(e)}")
        return None

    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        return bool(self._cache) and (time.time() - self._last_refresh < self._ttl)
