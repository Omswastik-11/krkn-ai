"""
Unit tests for krkn_ai.utils.endpoint_prober
"""

from unittest.mock import MagicMock, patch

import requests

from krkn_ai.utils.endpoint_prober import probe_endpoints


def _response(status_code: int) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    return resp


class TestProbeEndpoints:
    def test_empty_list_returns_empty_dict(self):
        assert probe_endpoints([]) == {}

    @patch("krkn_ai.utils.endpoint_prober.requests.get")
    def test_200_is_reachable(self, mock_get):
        mock_get.return_value = _response(200)
        result = probe_endpoints(["http://example.com/health"])
        assert result["http://example.com/health"] is True

    @patch("krkn_ai.utils.endpoint_prober.requests.get")
    def test_404_is_reachable(self, mock_get):
        """404 still means the server is up (< 500)."""
        mock_get.return_value = _response(404)
        result = probe_endpoints(["http://example.com/missing"])
        assert result["http://example.com/missing"] is True

    @patch("krkn_ai.utils.endpoint_prober.requests.get")
    def test_500_is_not_reachable(self, mock_get):
        mock_get.return_value = _response(500)
        assert (
            probe_endpoints(["http://example.com/err"])["http://example.com/err"]
            is False
        )

    @patch("krkn_ai.utils.endpoint_prober.requests.get")
    def test_503_is_not_reachable(self, mock_get):
        mock_get.return_value = _response(503)
        assert probe_endpoints(["http://example.com/"])["http://example.com/"] is False

    @patch(
        "krkn_ai.utils.endpoint_prober.requests.get",
        side_effect=requests.exceptions.ConnectionError(),
    )
    def test_connection_error_returns_false(self, _):
        assert (
            probe_endpoints(["http://down.internal/"])["http://down.internal/"] is False
        )

    @patch(
        "krkn_ai.utils.endpoint_prober.requests.get",
        side_effect=requests.exceptions.Timeout(),
    )
    def test_timeout_returns_false(self, _):
        assert (
            probe_endpoints(["http://slow.internal/"])["http://slow.internal/"] is False
        )

    @patch(
        "krkn_ai.utils.endpoint_prober.requests.get",
        side_effect=Exception("unexpected"),
    )
    def test_generic_exception_returns_false(self, _):
        assert probe_endpoints(["http://broken/"])["http://broken/"] is False

    @patch("krkn_ai.utils.endpoint_prober.requests.get")
    def test_multiple_urls_all_results_returned(self, mock_get):
        urls = ["http://a/", "http://b/", "http://c/"]
        mock_get.return_value = _response(200)
        result = probe_endpoints(urls)
        assert set(result.keys()) == set(urls)
        assert all(v for v in result.values())

    @patch("krkn_ai.utils.endpoint_prober.requests.get")
    def test_mixed_reachability(self, mock_get):
        def side_effect(url, **kw):
            if "ok" in url:
                return _response(200)
            raise requests.exceptions.ConnectionError()

        mock_get.side_effect = side_effect
        result = probe_endpoints(["http://ok/", "http://bad/"])
        assert result["http://ok/"] is True
        assert result["http://bad/"] is False

    @patch("krkn_ai.utils.endpoint_prober.requests.get")
    def test_respects_custom_timeout(self, mock_get):
        mock_get.return_value = _response(200)
        probe_endpoints(["http://example.com/"], timeout=2)
        _, kwargs = mock_get.call_args
        assert kwargs["timeout"] == 2
