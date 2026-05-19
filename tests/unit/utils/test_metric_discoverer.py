"""
Unit tests for krkn_ai.utils.metric_discoverer
"""

from unittest.mock import MagicMock


from krkn_ai.utils.metric_discoverer import (
    CHAOS_METRIC_CATALOGUE,
    _fetch_available_metrics,
    discover_fitness_functions,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _prom_client(available: set) -> MagicMock:
    client = MagicMock()
    client.process_query.return_value = [{"metric": {"__name__": m}} for m in available]
    return client


# ---------------------------------------------------------------------------
# Catalogue structure
# ---------------------------------------------------------------------------


class TestCatalogue:
    def test_all_entries_have_required_keys(self):
        required = {"template", "type", "priority", "description"}
        for metric, meta in CHAOS_METRIC_CATALOGUE.items():
            missing = required - set(meta.keys())
            assert not missing, f"'{metric}' missing keys: {missing}"

    def test_type_values_are_valid(self):
        for metric, meta in CHAOS_METRIC_CATALOGUE.items():
            assert meta["type"] in {"point", "range"}, (
                f"'{metric}' has invalid type '{meta['type']}'"
            )

    def test_templates_contain_ns_placeholder(self):
        for metric, meta in CHAOS_METRIC_CATALOGUE.items():
            assert "{ns}" in meta["template"], (
                f"'{metric}' template missing {{ns}} placeholder"
            )

    def test_priorities_are_unique(self):
        priorities = [m["priority"] for m in CHAOS_METRIC_CATALOGUE.values()]
        assert len(priorities) == len(set(priorities)), (
            "Duplicate priorities in catalogue"
        )


# ---------------------------------------------------------------------------
# discover_fitness_functions
# ---------------------------------------------------------------------------


class TestDiscoverFitnessFunctions:
    def test_empty_namespaces_returns_empty(self):
        client = _prom_client({"kube_pod_container_status_restarts_total"})
        assert discover_fitness_functions(client, []) == []

    def test_prom_unavailable_returns_empty(self):
        client = MagicMock()
        client.process_query.side_effect = Exception("connection refused")
        assert discover_fitness_functions(client, ["robot-shop"]) == []

    def test_no_matching_metrics_returns_empty(self):
        client = _prom_client({"some_custom_metric"})
        assert discover_fitness_functions(client, ["ns"]) == []

    def test_returns_suggestion_for_matching_metric(self):
        client = _prom_client({"kube_pod_container_status_restarts_total"})
        result = discover_fitness_functions(client, ["robot-shop"])
        assert len(result) == 1
        assert result[0]["metric"] == "kube_pod_container_status_restarts_total"
        assert result[0]["namespace"] == "robot-shop"
        assert result[0]["type"] == "point"

    def test_namespace_scoped_in_query(self):
        client = _prom_client({"kube_pod_container_status_restarts_total"})
        result = discover_fitness_functions(client, ["my-ns"])
        assert 'namespace="my-ns"' in result[0]["query"]

    def test_multiple_namespaces_generate_multiple_suggestions(self):
        client = _prom_client({"kube_pod_container_status_restarts_total"})
        result = discover_fitness_functions(client, ["ns-a", "ns-b"])
        namespaces = [r["namespace"] for r in result]
        assert "ns-a" in namespaces
        assert "ns-b" in namespaces

    def test_is_primary_set_for_highest_priority_first_namespace(self):
        client = _prom_client({"kube_pod_container_status_restarts_total"})
        result = discover_fitness_functions(client, ["primary-ns"])
        primary = [r for r in result if r["is_primary"]]
        assert len(primary) == 1
        assert primary[0]["namespace"] == "primary-ns"

    def test_results_sorted_by_priority(self):
        client = _prom_client(set(CHAOS_METRIC_CATALOGUE.keys()))
        result = discover_fitness_functions(client, ["ns"])
        priorities = [CHAOS_METRIC_CATALOGUE[r["metric"]]["priority"] for r in result]
        assert priorities == sorted(priorities)

    def test_unavailable_metrics_excluded(self):
        client = _prom_client({"up"})
        result = discover_fitness_functions(client, ["ns"])
        assert {r["metric"] for r in result} == {"up"}

    def test_each_suggestion_has_required_keys(self):
        client = _prom_client({"kube_pod_container_status_restarts_total", "up"})
        result = discover_fitness_functions(client, ["ns"])
        required = {"query", "type", "description", "metric", "namespace", "is_primary"}
        for suggestion in result:
            assert not (required - set(suggestion.keys()))


# ---------------------------------------------------------------------------
# _fetch_available_metrics
# ---------------------------------------------------------------------------


class TestFetchAvailableMetrics:
    def test_extracts_metric_names(self):
        client = MagicMock()
        client.process_query.return_value = [
            {"metric": {"__name__": "metric_a"}},
            {"metric": {"__name__": "metric_b"}},
        ]
        assert _fetch_available_metrics(client) == {"metric_a", "metric_b"}

    def test_returns_empty_on_exception(self):
        client = MagicMock()
        client.process_query.side_effect = Exception("unavailable")
        assert _fetch_available_metrics(client) == set()

    def test_returns_empty_when_query_returns_none(self):
        client = MagicMock()
        client.process_query.return_value = None
        assert _fetch_available_metrics(client) == set()

    def test_skips_series_without_name(self):
        client = MagicMock()
        client.process_query.return_value = [
            {"metric": {}},
            {"metric": {"__name__": "valid_metric"}},
        ]
        assert _fetch_available_metrics(client) == {"valid_metric"}
