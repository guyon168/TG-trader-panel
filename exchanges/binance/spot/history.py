"""Binance 现货历史成交查询"""
import time
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# 市值前 20 的主流币，当 get_all_tickers 失败时用作 fallback 排序权重
_MAJOR_COINS = {
    'BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'DOGE', 'ADA', 'AVAX',
    'DOT', 'LINK', 'MATIC', 'UNI', 'ATOM', 'LTC', 'ETC', 'FIL',
    'APT', 'ARB', 'OP', 'NEAR', 'INJ', 'TIA', 'SUI', 'SEI',
}
_STABLECOINS = {'USDT', 'USDC', 'BUSD', 'TUSD', 'FDUSD', 'DAI', 'USTC'}


class BinanceSpotHistoryMixin:
    """Binance 现货历史成交查询"""

    def get_positions_history_spot(self, symbol: Optional[str]) -> List[Dict[str, Any]]:
        """获取现货历史成交记录

        Binance 现货 get_my_trades 要求 symbol 参数，不能查全部交易对。
        symbol 未指定时：通过 get_all_tickers 一次性拉取全市场报价（1次API），
        按 USD 估值从高到低取前 MAX_COINS 个币种查询，避免灰尘币种触发429封禁。
        """
        MAX_COINS = 5
        history: List[Dict[str, Any]] = []
        try:
            if symbol:
                raw_s = self.format_symbol(symbol, 'spot')
                trades = self.client.get_my_trades(symbol=raw_s, limit=20)
                for t in trades:
                    history.append(self._format_trade_spot(t))
            else:
                bal = self.get_balance_spot()
                if not bal.get('total'):
                    return history

                try:
                    tickers = self.client.get_all_tickers()
                    price_map = {t['symbol']: float(t['price']) for t in tickers}
                except Exception:
                    price_map = {}
                    logger.warning("get_all_tickers 失败，使用余额数量排序作为 fallback")

                coin_values: Dict[str, float] = {}
                for ccy, amount in bal['total'].items():
                    if ccy == 'USDT':
                        continue
                    if ccy in _STABLECOINS:
                        coin_values[ccy] = amount
                    elif price_map:
                        pair = f"{ccy}USDT"
                        price = price_map.get(pair, 0)
                        coin_values[ccy] = amount * price if price > 0 else 0
                    else:
                        coin_values[ccy] = amount * 100 if ccy in _MAJOR_COINS else amount

                sorted_coins = sorted(
                    ((c, v) for c, v in coin_values.items()),
                    key=lambda x: x[1], reverse=True
                )
                top_coins = [(c, v) for c, v in sorted_coins[:MAX_COINS] if v > 0]

                if len(sorted_coins) > MAX_COINS:
                    skipped = [c for c, _ in sorted_coins[MAX_COINS:MAX_COINS + 5]]
                    top_names = [f"{c}(${v:.2f})" for c, v in top_coins]
                    logger.info(f"现货 /history: 共{len(sorted_coins)}个币种，"
                                f"查询TOP{MAX_COINS}: {top_names}, "
                                f"跳过: {skipped}...")

                for ccy, _ in top_coins:
                    try:
                        pair = self.format_symbol(ccy, 'spot')
                        trades = self.client.get_my_trades(symbol=pair, limit=5)
                        for t in trades:
                            history.append(self._format_trade_spot(t))
                        time.sleep(0.3)
                    except Exception:
                        pass
            return history
        except Exception as e:
            logger.error(f"Binance 获取现货历史记录失败: {str(e)}")
            return []

    @staticmethod
    def _format_trade_spot(t: Dict[str, Any]) -> Dict[str, Any]:
        """将 Binance 现货单笔成交记录转为统一格式"""
        return {
            'symbol': t.get('symbol'),
            'display_symbol': t.get('symbol'),
            'side': 'BUY' if t.get('isBuyer') else 'SELL',
            'openAvgPx': float(t.get('price', 0)),
            'pnl': 0,
            'sz': float(t.get('qty', 0)),
            'mgnMode': 'SPOT',
            'openTime': t.get('time', 0),
            'unit': '个'
        }
