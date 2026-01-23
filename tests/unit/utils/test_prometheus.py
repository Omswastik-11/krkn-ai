"""
Unit tests for Prometheus utility functions and client creation logic.
"""

import os
import json
import pytest
from unittest.mock import Mock, patch
from krkn_ai.utils.prometheus import is_openshift, create_prometheus_client
from krkn_ai.models.custom_errors import PrometheusConnectionError


class TestPrometheusUtils:
    """Tests for Prometheus utility functions."""

    def test_is_openshift_positive(self):
        """Should return True when clusterversions resource is found."""
        with patch("krkn_ai.utils.prometheus.run_shell", return_value=("", 0)):
            assert is_openshift("/tmp/test-kubeconfig") is True

    def test_is_openshift_negative(self):
        """Should return False when clusterversions resource is missing."""
        with patch("krkn_ai.utils.prometheus.run_shell", return_value=("", 1)):
            assert is_openshift("/tmp/test-kubeconfig") is False

    @patch("krkn_ai.utils.prometheus.KrknPrometheus")
    def test_create_client_from_env_vars(self, mock_prom_class):
        """Should prioritize PROMETHEUS_URL and PROMETHEUS_TOKEN from environment."""
        env = {
            "PROMETHEUS_URL": "prometheus.example.com",
            "PROMETHEUS_TOKEN": "secret-token",
        }
        with patch.dict(os.environ, env):
            mock_client = Mock()
            mock_client.process_query.return_value = None
            mock_prom_class.return_value = mock_client

            client = create_prometheus_client("/tmp/test-kubeconfig")

            mock_prom_class.assert_called_once_with(
                "https://prometheus.example.com", "secret-token"
            )
            assert client == mock_client

    @patch("krkn_ai.utils.prometheus.is_openshift", return_value=True)
    @patch("krkn_ai.utils.prometheus.KrknPrometheus")
    def test_create_client_autodiscovery_openshift(self, mock_prom_class, _):
        """Should auto-discover URL and token on OpenShift clusters."""
        route_data = {"items": [{"spec": {"host": "thanos-query.apps.cluster.com"}}]}

        with patch.dict(os.environ, {}, clear=True):
            with patch("krkn_ai.utils.prometheus.run_shell") as mock_shell:
                # 1. Route discovery, 2. Token discovery
                mock_shell.side_effect = [
                    (json.dumps(route_data), 0),
                    ("oc-token", 0),
                ]

                mock_client = Mock()
                mock_client.process_query.return_value = None
                mock_prom_class.return_value = mock_client

                client = create_prometheus_client("/tmp/test-kubeconfig")

                mock_prom_class.assert_called_once()
                args, _ = mock_prom_class.call_args
                assert args[0] == "https://thanos-query.apps.cluster.com"
                assert args[1] == "oc-token"
                assert client == mock_client

    @patch("krkn_ai.utils.prometheus.is_openshift", return_value=False)
    def test_create_client_missing_config_vanilla_k8s(self, _):
        """Should raise connection error on vanilla K8s if env vars are missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(PrometheusConnectionError) as exc:
                create_prometheus_client("/tmp/test-kubeconfig")
            assert "Prometheus configuration missing" in str(exc.value)

    @patch("krkn_ai.utils.prometheus.is_openshift", return_value=True)
    def test_create_client_autodiscovery_failure_openshift(self, _):
        """Should raise connection error if discovery fails on OpenShift."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("krkn_ai.utils.prometheus.run_shell", return_value=("", 1)):
                with pytest.raises(PrometheusConnectionError) as exc:
                    create_prometheus_client("/tmp/test-kubeconfig")
                assert "discovery failed on OpenShift" in str(exc.value)

    @patch("krkn_ai.utils.prometheus.is_openshift", return_value=True)
    def test_create_client_malformed_route_openshift(self, _):
        """Should handle empty route lists gracefully on OpenShift."""
        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "krkn_ai.utils.prometheus.run_shell", return_value=('{"items": []}', 0)
            ):
                with pytest.raises(PrometheusConnectionError):
                    create_prometheus_client("/tmp/test-kubeconfig")

    @patch("krkn_ai.utils.prometheus.KrknPrometheus")
    def test_create_client_connection_test_failure(self, mock_prom_class):
        """Should raise connection error if the connection test (process_query) fails."""
        env = {"PROMETHEUS_URL": "http://localhost", "PROMETHEUS_TOKEN": "tok"}
        with patch.dict(os.environ, env):
            mock_client = Mock()
            mock_client.process_query.side_effect = Exception("Auth failed")
            mock_prom_class.return_value = mock_client

            with pytest.raises(PrometheusConnectionError) as exc:
                create_prometheus_client("/tmp/test-kubeconfig")
            assert "Failed to connect to Prometheus" in str(exc.value)

    @patch("krkn_ai.utils.prometheus.KrknPrometheus")
    def test_url_protocol_enforcement(self, mock_prom_class):
        """Should enforce https:// prefix if protocol is missing."""
        env = {"PROMETHEUS_URL": "my-prom", "PROMETHEUS_TOKEN": "tok"}
        with patch.dict(os.environ, env):
            mock_client = Mock()
            mock_prom_class.return_value = mock_client

            create_prometheus_client("/tmp/test-kubeconfig")
            args, _ = mock_prom_class.call_args
            assert args[0] == "https://my-prom"
