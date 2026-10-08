"""Unit tests for backend.dynamo_cache module."""

import time
from unittest.mock import MagicMock, patch
from backend.dynamo_cache import (
    get_cached_result,
    make_cache_key,
    store_demo_scenario,
    store_result,
)


def test_make_cache_key() -> None:
    """Verify cache key derivation and length."""
    k1 = make_cache_key("28.6315,77.2167", "28.5491,77.2520", "driving", 8)
    k2 = make_cache_key("28.6315,77.2167", "28.5491,77.2520", "driving", 8)
    k3 = make_cache_key("28.6315,77.2167", "28.5491,77.2520", "walking", 8)
    assert len(k1) == 32
    assert k1 == k2
    assert k1 != k3


def test_get_cached_result_hit_and_expired() -> None:
    """Verify hit returns result, expired returns None."""
    mock_table = MagicMock()
    now = int(time.time())

    # Valid non-expired item
    mock_table.get_item.return_value = {
        "Item": {
            "cache_key": "abc",
            "payload": '{"routes": []}',
            "expires_at": now + 1000,
        }
    }
    with patch("backend.dynamo_cache._get_table", return_value=mock_table):
        res = get_cached_result("abc")
        assert res == {"routes": []}

    # Expired item
    mock_table.get_item.return_value = {
        "Item": {
            "cache_key": "abc",
            "payload": '{"routes": []}',
            "expires_at": now - 100,
        }
    }
    with patch("backend.dynamo_cache._get_table", return_value=mock_table):
        res_expired = get_cached_result("abc")
        assert res_expired is None


def test_store_result_and_demo_scenario() -> None:
    """Verify store_result and store_demo_scenario write to table."""
    mock_table = MagicMock()
    with patch("backend.dynamo_cache._get_table", return_value=mock_table):
        store_result("key1", {"status": "ok"}, ttl_hours=1)
        assert mock_table.put_item.call_count == 1
        call_item = mock_table.put_item.call_args[1]["Item"]
        assert call_item["cache_key"] == "key1"
        assert "payload" in call_item
        assert call_item["expires_at"] > time.time()

        store_demo_scenario()
        assert mock_table.put_item.call_count == 2
        demo_item = mock_table.put_item.call_args[1]["Item"]
        assert demo_item["expires_at"] == 9999999999
