"""Unit tests for core/base_client.py — Abstract method structure verification"""
import pytest
from abc import ABC
from core.base_client import BaseExchangeClient


class TestBaseExchangeClient:
    """Tests for BaseExchangeClient abstract base class"""

    def test_is_abstract_class(self):
        assert issubclass(BaseExchangeClient, ABC)

    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            BaseExchangeClient()

    def test_has_11_abstract_methods(self):
        abstract_methods = BaseExchangeClient.__abstractmethods__
        assert len(abstract_methods) == 11, \
            f"Expected 11 abstract methods, got {len(abstract_methods)}: {abstract_methods}"

    def test_required_abstract_methods_exist(self):
        required = {
            'format_symbol', 'get_price', 'get_balance', 'get_positions',
            'get_positions_history', 'get_open_orders', 'place_market_order',
            'place_limit_order', 'place_tpsl', 'place_trailing_stop', 'cancel_orders'
        }
        abstract_methods = BaseExchangeClient.__abstractmethods__
        assert required == abstract_methods, \
            f"Abstract methods mismatch. Expected: {required}, Got: {abstract_methods}"

    def test_concrete_class_must_implement_all(self):
        """Verify a partial implementation cannot be instantiated"""

        class PartialImpl(BaseExchangeClient):
            exchange_name = 'test'
            # Only implement one method

            def format_symbol(self, symbol, mode):
                return symbol

        with pytest.raises(TypeError):
            PartialImpl()

    def test_full_concrete_class_can_instantiate(self):
        """Verify a full implementation can be instantiated"""

        class FullImpl(BaseExchangeClient):
            exchange_name = 'test'

            def format_symbol(self, symbol, mode):
                return symbol

            def get_price(self, symbol, mode):
                return 0.0

            def get_balance(self, mode):
                return {}

            def get_positions(self, mode):
                return []

            def get_positions_history(self, symbol, mode):
                return []

            def get_open_orders(self, symbol, mode):
                return []

            def place_market_order(self, symbol, side, amount, is_usdt, mode,
                                   leverage, margin_mode):
                return {}

            def place_limit_order(self, symbol, side, amount, price, is_usdt,
                                  mode, leverage, margin_mode):
                return {}

            def place_tpsl(self, symbol, side, amount, tp, sl, mode, margin_mode):
                return {}

            def place_trailing_stop(self, symbol, side, amount, callback_ratio,
                                    active_px, is_usdt, mode, leverage, margin_mode):
                return {}

            def cancel_orders(self, symbol, order_id, mode):
                return 0

        instance = FullImpl()
        assert instance.exchange_name == 'test'
