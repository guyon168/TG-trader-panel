"""OKX 持仓模式自动检测，缓存 TTL 5分钟

修复 BUG-1: OKX posSide='net' 硬编码 → 通过 API 动态检测
"""
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class PosSideDetector:
    """OKX 持仓模式自动检测

    原始代码中 posSide 统一硬编码为 'net'，导致双向持仓模式下无法正确下单。
    本类通过 API 查询账户持仓模式，并缓存结果以减少 API 调用。

    逻辑:
        - mode != 'future' → 返回 '' (现货不需要 posSide)
        - net_mode → 'net'
        - long_short_mode → buy→'long', sell→'short'
    """

    CACHE_TTL = 300  # 5 分钟

    def __init__(self, adapter, cache_ttl: int = CACHE_TTL):
        self._adapter = adapter
        self._pos_mode: Optional[str] = None
        self._last_detect: float = 0
        self._cache_ttl = cache_ttl

    def get_pos_side(self, inst_id: str, mode: str, side: str) -> str:
        """根据持仓模式和方向，返回 posSide 参数值

        Args:
            inst_id: 交易对 instId
            mode: 'spot' 或 'future'
            side: 'buy' 或 'sell'（小写）

        Returns:
            posSide 值: '' (现货), 'net' (净仓模式), 'long'/'short' (双向持仓)
        """
        # 现货不需要 posSide
        if mode != 'future':
            return ''

        pos_mode = self._get_pos_mode()

        if pos_mode == 'net_mode':
            return 'net'
        elif pos_mode == 'long_short_mode':
            side_lower = side.lower() if isinstance(side, str) else str(side).lower()
            return 'long' if side_lower == 'buy' else 'short'
        else:
            # 未知模式，默认 net
            logger.warning(f"PosSideDetector: 未知持仓模式 {pos_mode}，默认使用 net")
            return 'net'

    def invalidate(self):
        """手动失效缓存，下次调用时重新查询"""
        self._pos_mode = None
        self._last_detect = 0

    def _get_pos_mode(self) -> str:
        """带缓存的 API 查询"""
        if self._pos_mode is not None and (time.time() - self._last_detect < self._cache_ttl):
            return self._pos_mode

        try:
            res = self._adapter.get_positions(instId='', instType='SWAP')
            # OKX 通过返回数据中的 posSide 字段推断持仓模式
            # 如果有 long/short 字样 → 双向持仓模式
            if res.get('code') == '0' and res.get('data'):
                for pos in res['data']:
                    ps = pos.get('posSide', '')
                    if ps in ['long', 'short']:
                        self._pos_mode = 'long_short_mode'
                        self._last_detect = time.time()
                        return self._pos_mode

            # 尝试通过 account_config 获取
            try:
                config_res = self._adapter.get_account_config()
                if config_res.get('code') == '0' and config_res.get('data'):
                    for acc in config_res['data']:
                        pm = acc.get('posMode', '')
                        if pm:
                            self._pos_mode = pm
                            self._last_detect = time.time()
                            return self._pos_mode
            except Exception:
                pass

            # 默认 net_mode
            self._pos_mode = 'net_mode'
            self._last_detect = time.time()
        except Exception as e:
            logger.error(f"PosSideDetector: 查询持仓模式失败 - {str(e)}")
            self._pos_mode = 'net_mode'
            self._last_detect = time.time()

        return self._pos_mode
