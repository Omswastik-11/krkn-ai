import os
import json
from krkn_lib.prometheus.krkn_prometheus import KrknPrometheus
from krkn_ai.utils import run_shell
from krkn_ai.utils.fs import env_is_truthy
from krkn_ai.utils.logger import get_logger
from krkn_ai.models.custom_errors import PrometheusConnectionError

logger = get_logger(__name__)


def is_openshift(kubeconfig: str) -> bool:
    """
    Checks if the targeted cluster is an OpenShift cluster.

    Attempts to query OpenShift cluster versions via kubectl.

    Args:
        kubeconfig: Path to the Kubernetes configuration file.

    Returns:
        True if the cluster is OpenShift, False otherwise.
    """
    _, returncode = run_shell(
        f"kubectl --kubeconfig={kubeconfig} get clusterversions.config.openshift.io",
        do_not_log=True,
    )
    return returncode == 0


def create_prometheus_client(kubeconfig: str) -> KrknPrometheus:
    """
    Creates a Prometheus client with intelligent discovery and fallback logic.

    Discovery Priority:
    1. Explicit environment variables: `PROMETHEUS_URL` and `PROMETHEUS_TOKEN`.
    2. OpenShift Auto-discovery: If the cluster is OpenShift, attempts to discover
       the URL from routes and the token via `oc whoami`.
    3. Error: Raises `PrometheusConnectionError` with actionable instructions.

    Args:
        kubeconfig: Path to the Kubernetes configuration file.

    Returns:
        A configured KrknPrometheus client instance.

    Raises:
        PrometheusConnectionError: If Prometheus cannot be discovered or accessed.
    """
    url = os.getenv("PROMETHEUS_URL", "").strip()
    token = os.getenv("PROMETHEUS_TOKEN", "").strip()

    # Case 1: Both environment variables provided
    if url and token:
        return _validate_and_create_client(url, token)

    is_ocp = is_openshift(kubeconfig)

    # Case 2: Vanilla Kubernetes or missing env vars on non-OCP
    if not is_ocp:
        if not url or not token:
            raise PrometheusConnectionError(
                "Prometheus configuration missing for Kubernetes cluster.\n"
                "Please set the following environment variables:\n"
                "  export PROMETHEUS_URL=https://<prometheus-host>\n"
                "  export PROMETHEUS_TOKEN=<bearer-token>\n\n"
                "For generic Kubernetes clusters, explicit configuration is required."
            )
        return _validate_and_create_client(url, token)

    # Case 3: OpenShift Auto-discovery
    if not url:
        url = _discover_openshift_prometheus_url(kubeconfig)

    if not token:
        token = _discover_openshift_prometheus_token(kubeconfig)

    if not url or not token:
        raise PrometheusConnectionError(
            "Automatic Prometheus discovery failed on OpenShift.\n"
            "Ensure the monitoring routes are accessible or set explicitly:\n"
            "  export PROMETHEUS_URL=<discovered-url>\n"
            "  export PROMETHEUS_TOKEN=$(oc whoami -t)"
        )

    return _validate_and_create_client(url, token)


def _discover_openshift_prometheus_url(kubeconfig: str) -> str:
    """
    Attempts to discover the Prometheus (Thanos Query) URL from OpenShift routes.

    Args:
        kubeconfig: Path to the Kubernetes configuration file.

    Returns:
        The discovered host URL or an empty string if discovery fails.
    """
    try:
        prom_spec_json, code = run_shell(
            f"kubectl --kubeconfig={kubeconfig} -n openshift-monitoring "
            "get route -l app.kubernetes.io/name=thanos-query -o json",
            do_not_log=True,
        )
        if code != 0:
            logger.debug("Failed to fetch Prometheus route from OpenShift")
            return ""

        prom_spec = json.loads(prom_spec_json)
        items = prom_spec.get("items", [])
        if not items:
            logger.debug("No Prometheus Thanos Query routes found")
            return ""

        # Safely extract host from the first route
        host = items[0].get("spec", {}).get("host", "").strip()
        return host
    except Exception as e:
        logger.debug(f"Unexpected error during URL discovery: {e}")
        return ""


def _discover_openshift_prometheus_token(kubeconfig: str) -> str:
    """
    Attempts to discover an authentication token using the OpenShift CLI.

    Args:
        kubeconfig: Path to the Kubernetes configuration file.

    Returns:
        The authentication token or an empty string if discovery fails.
    """
    try:
        token, code = run_shell(
            f"oc --kubeconfig={kubeconfig} whoami -t",
            do_not_log=True,
        )
        if code != 0:
            logger.debug("Failed to retrieve token via 'oc whoami -t'")
            return ""
        return token.strip()
    except Exception as e:
        logger.debug(f"Unexpected error during token discovery: {e}")
        return ""


def _validate_and_create_client(url: str, token: str) -> KrknPrometheus:
    """
    Validates connection parameters and initializes the Prometheus client.

    Args:
        url: The Prometheus API endpoint URL.
        token: Authentication token.

    Returns:
        An initialized KrknPrometheus client.

    Raises:
        PrometheusConnectionError: If the connection test fails.
    """
    # Ensure URL has a protocol scheme
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    logger.debug(f"Initializing Prometheus client: {url}")

    try:
        client = KrknPrometheus(url.strip(), token.strip())
        # Connection test: run a dummy query unless in mock mode
        if not env_is_truthy("MOCK_FITNESS"):
            client.process_query("1")
        return client
    except Exception as e:
        raise PrometheusConnectionError(
            f"Failed to connect to Prometheus at {url}.\n"
            f"Error details: {str(e)}\n\n"
            "Check network connectivity and ensure the token is valid."
        )
