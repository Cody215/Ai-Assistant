import pytest
from llm.formatters import format_response


def test_format_response_empty_time_returns_none():
    assert format_response("get_time", "") is None


def test_format_response_whitespace_battery_returns_none():
    assert format_response("get_battery", "   \n\t ") is None


def test_format_response_empty_system_status_returns_string():
    # get_system_status treats empty as OK and returns a string
    res = format_response("get_system_status", "")
    assert isinstance(res, str) and res
