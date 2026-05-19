"""
Concurrent HTTP reachability checks for health-check URL discovery.

Used by the `discover` command to separate live endpoints (rendered as
active health-checks in the generated config) from unreachable ones
(rendered as commented-out suggestions).
"""

from typing import Dict, List

import requests

from krkn_ai.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_TIMEOUT = 5
DEFAULT_WORKERS = 10


def probe_endpoints(
    urls: List[str],
    timeout: int = DEFAULT_TIMEOUT,
    max_workers: int = DEFAULT_WORKERS,
) -> Dict[str, bool]:
    """Probe a list of URLs concurrently and return a reachability map.

    Args:
        urls:        List of HTTP/HTTPS URLs to probe.
        timeout:     Per-request timeout in seconds.
        max_workers: Maximum concurrent probe threads.

    Returns:
        Dict mapping each URL to True (reachable) or False (unreachable).
        A URL is considered reachable if it responds with HTTP < 500.
    """
    if not urls:
        return {}

    from concurrent.futures import ThreadPoolExecutor, as_completed

    results: Dict[str, bool] = {}

    def _probe(url: str) -> tuple:
        try:
            resp = requests.get(
                url, timeout=timeout, allow_redirects=True, verify=False
            )
            reachable = resp.status_code < 500
            logger.debug(
                "Probe %s -> HTTP %s (reachable=%s)", url, resp.status_code, reachable
            )
            return url, reachable
        except requests.exceptions.ConnectionError:
            logger.debug("Probe %s -> connection refused", url)
            return url, False
        except requests.exceptions.Timeout:
            logger.debug("Probe %s -> timed out after %ss", url, timeout)
            return url, False
        except Exception as exc:
            logger.debug("Probe %s -> error: %s", url, exc)
            return url, False

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(_probe, u): u for u in urls}
        for future in as_completed(future_to_url):
            url, reachable = future.result()
            results[url] = reachable

    reachable_count = sum(1 for v in results.values() if v)
    logger.debug(
        "Probed %d URLs: %d reachable, %d unreachable",
        len(urls),
        reachable_count,
        len(urls) - reachable_count,
    )
    return results
