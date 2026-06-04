"""交易所客户端抽象基类"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, List


class BaseExchangeClient(ABC):
    """交易所客户端抽象基类，定义所有交易所必须实现的接口"""

    exchange_name: str  # 子类必须设置

    @abstractmethod
    def format_symbol(self, symbol: str, mode: str) -> str:
        """将用户输入的币种转为交易所 instId/symbol 格式"""

    @abstractmethod
    def get_price(self, symbol: str, mode: str) -> float:
        """获取最新价格"""

    @abstractmethod
    def get_balance(self, mode: str) -> Dict[str, Any]:
        """获取余额"""

    @abstractmethod
    def get_positions(self, mode: str) -> List[Dict[str, Any]]:
        """获取持仓列表"""

    @abstractmethod
    def get_positions_history(self, symbol: Optional[str], mode: str) -> List[Dict[str, Any]]:
        """获取历史仓位"""

    @abstractmethod
    def get_open_orders(self, symbol: Optional[str], mode: str) -> List[Dict[str, Any]]:
        """获取当前挂单"""

    @abstractmethod
    def place_market_order(self, symbol: str, side: str, amount: float,
                           is_usdt: bool, mode: str, leverage: int,
                           margin_mode: str) -> Dict[str, Any]:
        """市价下单"""

    @abstractmethod
    def place_limit_order(self, symbol: str, side: str, amount: float,
                          price: float, is_usdt: bool, mode: str,
                          leverage: int, margin_mode: str) -> Dict[str, Any]:
        """限价下单"""

    @abstractmethod
    def place_tpsl(self, symbol: str, side: str, amount: float,
                   tp: Optional[float], sl: Optional[float], mode: str,
                   margin_mode: str, reduce_only: bool = False) -> Dict[str, Any]:
        """止盈止损条件单"""

    @abstractmethod
    def place_trailing_stop(self, symbol: str, side: str, amount: float,
                            callback_ratio: float, active_px: Optional[float],
                            is_usdt: bool, mode: str, leverage: int,
                            margin_mode: str, reduce_only: bool = False) -> Dict[str, Any]:
        """移动止损"""

    @abstractmethod
    def cancel_orders(self, symbol: Optional[str], order_id: Optional[str],
                      mode: str) -> int:
        """撤销订单"""

    @abstractmethod
    def set_leverage(self, symbol: str, leverage: int, margin_mode: str) -> Dict[str, Any]:
        """设置合约杠杆和保证金模式"""
