"""OKX 操作适配层 — 隔离 SDK 实现细节

将 OKX Python SDK (TradeAPI / AccountAPI / MarketDataAPI) 统一包装，
所有 Mixin 通过 self._adapter.xxx() 调用，不直接依赖 SDK 对象。

将来如需切换到 CLI 或 MCP Server，只需实现一个新 Adapter 即可，
所有 Mixin 和 handler 代码无需修改。
"""


class OKXAdapter:
    """OKX 操作适配器，聚合 Trade / Account / Market / Public 四类 API"""

    def __init__(self, trade_api, account_api, market_api, public_api=None):
        self.trade = trade_api
        self.account = account_api
        self.market = market_api
        self.public = public_api

    # ---- 委托下单 ----
    def place_order(self, inst_id: str, td_mode: str, side: str,
                    ord_type: str, sz: str, **kwargs):
        return self.trade.place_order(inst_id, td_mode, side, ord_type, sz, **kwargs)

    def place_algo_order(self, **params):
        return self.trade.place_algo_order(**params)

    # ---- 撤单 ----
    def cancel_order(self, **kwargs):
        return self.trade.cancel_order(**kwargs)

    def cancel_algo_order(self, params: list):
        return self.trade.cancel_algo_order(params)

    def cancel_multiple_orders(self, params: list):
        return self.trade.cancel_multiple_orders(params)

    # ---- 挂单查询 ----
    def get_order_list(self, **kwargs):
        return self.trade.get_order_list(**kwargs)

    def order_algos_list(self, **kwargs):
        return self.trade.order_algos_list(**kwargs)

    # ---- 账户 ----
    def get_account_balance(self):
        return self.account.get_account_balance()

    def get_positions(self, **kwargs):
        return self.account.get_positions(**kwargs)

    def get_positions_history(self, **kwargs):
        return self.account.get_positions_history(**kwargs)

    def get_account_config(self):
        return self.account.get_account_config()

    def set_leverage(self, **kwargs):
        return self.account.set_leverage(**kwargs)

    # ---- 行情 ----
    def get_ticker(self, inst_id: str):
        return self.market.get_ticker(instId=inst_id)

    def get_tickers(self, inst_type: str):
        return self.market.get_tickers(instType=inst_type)

    def get_instruments(self, **kwargs):
        return self.public.get_instruments(**kwargs) if self.public else self.market.get_instruments(**kwargs)
