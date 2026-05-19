"""
Discovers available Prometheus metrics and suggests scoped PromQL fitness functions.

Used during `discover` to populate the fitness_function section of the generated
config with real, namespace-scoped queries instead of the hardcoded default.
Degrades gracefully when Prometheus is unreachable.
"""

from typing import Any, Dict, List

from krkn_ai.utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Catalogue of chaos-relevant Prometheus metrics.
# priority: lower = rendered first / used as primary fitness function.
# ---------------------------------------------------------------------------
CHAOS_METRIC_CATALOGUE: Dict[str, Dict[str, Any]] = {
    "kube_pod_container_status_restarts_total": {
        "template": 'sum(kube_pod_container_status_restarts_total{{namespace="{ns}"}})',
        "type": "point",
        "priority": 1,
        "description": "Pod restart delta — spikes when chaos disrupts workloads",
    },
    "kube_pod_status_phase": {
        "template": (
            'count(kube_pod_status_phase{{namespace="{ns}",phase!="Running"}}) or vector(0)'
        ),
        "type": "point",
        "priority": 2,
        "description": "Non-Running pod count — increases during disruption",
    },
    "container_cpu_usage_seconds_total": {
        "template": (
            "sum(rate(container_cpu_usage_seconds_total"
            '{{namespace="{ns}",container!=""}}[$range$]))'
        ),
        "type": "range",
        "priority": 3,
        "description": "CPU usage rate — suited for node-cpu-hog scenarios",
    },
    "container_memory_working_set_bytes": {
        "template": (
            'max(container_memory_working_set_bytes{{namespace="{ns}",container!=""}})'
        ),
        "type": "range",
        "priority": 4,
        "description": "Peak memory — suited for node-memory-hog scenarios",
    },
    "up": {
        "template": 'min(up{{namespace="{ns}"}})',
        "type": "point",
        "priority": 5,
        "description": "Service availability (0=down) — general resilience proxy",
    },
    "http_requests_total": {
        "template": (
            'sum(rate(http_requests_total{{namespace="{ns}",code=~"5.."}}[$range$]))'
        ),
        "type": "range",
        "priority": 6,
        "description": "HTTP 5xx error rate — application-level chaos impact",
    },
    "kube_deployment_status_replicas_unavailable": {
        "template": (
            'sum(kube_deployment_status_replicas_unavailable{{namespace="{ns}"}})'
        ),
        "type": "point",
        "priority": 7,
        "description": "Unavailable replicas — deployment disruption signal",
    },
}


def discover_fitness_functions(
    prom_client: Any,
    namespaces: List[str],
) -> List[Dict[str, Any]]:
    """Query Prometheus for available metrics and return fitness function suggestions.

    Each suggestion is scoped to a discovered namespace.  The list is sorted
    by catalogue priority so callers can use the first entry as the primary
    fitness function and the rest as commented-out alternatives.

    Args:
        prom_client: An initialised KrknPrometheus client.
        namespaces:  Namespace names to scope queries to.

    Returns:
        List of suggestion dicts with keys:
            query, type, description, metric, namespace, is_primary.
        Returns an empty list if Prometheus is unreachable or no metrics match.
    """
    if not namespaces:
        logger.debug("No namespaces provided; skipping metric discovery")
        return []

    available = _fetch_available_metrics(prom_client)
    if not available:
        logger.warning(
            "Could not retrieve metric list from Prometheus; "
            "falling back to default fitness function"
        )
        return []

    logger.debug("Prometheus reports %d available metrics", len(available))

    suggestions: List[Dict[str, Any]] = []
    for metric_name, meta in sorted(
        CHAOS_METRIC_CATALOGUE.items(), key=lambda x: x[1]["priority"]
    ):
        if metric_name not in available:
            logger.debug("Metric '%s' not in Prometheus — skipping", metric_name)
            continue
        for i, ns in enumerate(namespaces):
            query = meta["template"].format(ns=ns)
            suggestions.append(
                {
                    "query": query,
                    "type": meta["type"],
                    "description": meta["description"],
                    "metric": metric_name,
                    "namespace": ns,
                    "is_primary": (i == 0 and meta["priority"] == 1),
                }
            )

    logger.debug(
        "Generated %d fitness function suggestions from %d catalogue entries",
        len(suggestions),
        len(CHAOS_METRIC_CATALOGUE),
    )
    return suggestions


def _fetch_available_metrics(prom_client: Any) -> set:
    """Return the set of metric names available in Prometheus.

    Returns an empty set on any failure so callers degrade gracefully.
    """
    try:
        result = prom_client.process_query('group by(__name__)({__name__=~".+"})')
        if not result:
            return set()
        names: set = set()
        for series in result:
            name = series.get("metric", {}).get("__name__", "")
            if name:
                names.add(name)
        return names
    except Exception as exc:
        logger.debug("Failed to fetch metric names from Prometheus: %s", exc)
        return set()
