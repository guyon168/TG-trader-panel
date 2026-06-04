"""Unit tests for utils/helpers.py"""
import pytest
from utils.helpers import parse_amount, escape_markdown


class TestParseAmount:
    """Tests for parse_amount utility function"""

    def test_plain_number(self):
        amount, is_usdt = parse_amount("100")
        assert amount == 100.0
        assert is_usdt is False

    def test_decimal_number(self):
        amount, is_usdt = parse_amount("0.5")
        assert amount == 0.5
        assert is_usdt is False

    def test_usdt_suffix(self):
        amount, is_usdt = parse_amount("100u")
        assert amount == 100.0
        assert is_usdt is True

    def test_usdt_full_suffix(self):
        amount, is_usdt = parse_amount("100usdt")
        assert amount == 100.0
        assert is_usdt is True

    def test_decimal_with_u(self):
        amount, is_usdt = parse_amount("50.5u")
        assert amount == 50.5
        assert is_usdt is True

    def test_decimal_with_usdt(self):
        amount, is_usdt = parse_amount("50.5usdt")
        assert amount == 50.5
        assert is_usdt is True

    def test_case_insensitive(self):
        amount, is_usdt = parse_amount("100U")
        assert amount == 100.0
        assert is_usdt is True

    def test_invalid_number(self):
        with pytest.raises(ValueError):
            parse_amount("abc")

    def test_invalid_number_with_u(self):
        with pytest.raises(ValueError):
            parse_amount("abcu")

    def test_whitespace_handling(self):
        amount, is_usdt = parse_amount("  100u  ")
        assert amount == 100.0
        assert is_usdt is True


class TestEscapeMarkdown:
    """Tests for escape_markdown utility function"""

    def test_escape_underscore(self):
        assert escape_markdown("hello_world") == "hello\\_world"

    def test_escape_asterisk(self):
        assert escape_markdown("hello*world") == "hello\\*world"

    def test_escape_backtick(self):
        assert escape_markdown("hello`world") == "hello\\`world"

    def test_escape_bracket(self):
        assert escape_markdown("hello[world") == "hello\\[world"

    def test_escape_multiple(self):
        result = escape_markdown("_*`[")
        assert result == "\\_\\*\\`\\["

    def test_no_escape_needed(self):
        assert escape_markdown("hello world") == "hello world"

    def test_non_string_input(self):
        result = escape_markdown(123)
        assert result == "123"

    def test_empty_string(self):
        assert escape_markdown("") == ""
