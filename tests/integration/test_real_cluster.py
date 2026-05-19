"""
Integration test: run scenario_selector and endpoint_prober against a real Kind cluster.

This script:
  1. Connects to an existing Kind cluster using the real kubeconfig
  2. Runs ClusterManager.discover_components() to get real cluster state
  3. Feeds that into scenario_selector.select_scenarios() and prints results
  4. Discovers service endpoints and feeds them into endpoint_prober.probe_endpoints()
  5. Writes all output to a JSON artifact for proposal evidence

Usage:
    python tests/integration/test_real_cluster.py [--kubeconfig PATH]
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from krkn_ai.utils.cluster_manager import ClusterManager
from krkn_ai.utils.scenario_selector import select_scenarios
from krkn_ai.utils.endpoint_prober import probe_endpoints


def main():
    parser = argparse.ArgumentParser(description="Real-cluster integration test")
    parser.add_argument(
        "--kubeconfig",
        default=os.environ.get("KUBECONFIG", os.path.expanduser("~/.kube/config")),
        help="Path to kubeconfig",
    )
    parser.add_argument(
        "--output",
        default="tests/integration/cluster_test_results.json",
        help="Output JSON artifact path",
    )
    args = parser.parse_args()

    print(f"[1/5] Connecting to cluster using kubeconfig: {args.kubeconfig}")
    cm = ClusterManager(args.kubeconfig)

    print("[2/5] Discovering cluster components (all namespaces)...")
    components = cm.discover_components(namespace_pattern=".*")

    # Summarise what was found
    ns_names = [ns.name for ns in components.namespaces]
    total_pods = sum(len(ns.pods) for ns in components.namespaces)
    total_services = sum(len(ns.services) for ns in components.namespaces)
    total_pvcs = sum(len(ns.pvcs) for ns in components.namespaces)
    total_vmis = sum(len(ns.vmis) for ns in components.namespaces)
    node_names = [n.name for n in components.nodes]
    node_interfaces = {n.name: n.interfaces for n in components.nodes}

    discovery_summary = {
        "namespaces": ns_names,
        "namespace_count": len(ns_names),
        "total_pods": total_pods,
        "total_services": total_services,
        "total_pvcs": total_pvcs,
        "total_vmis": total_vmis,
        "nodes": node_names,
        "node_count": len(node_names),
        "node_interfaces": node_interfaces,
    }
    print(
        f"    Found: {len(ns_names)} namespaces, {total_pods} pods, "
        f"{total_services} services, {len(node_names)} nodes"
    )

    print("[3/5] Running scenario_selector.select_scenarios()...")
    scenario_flags = select_scenarios(components)
    enabled = [k for k, v in scenario_flags.items() if v]
    disabled = [k for k, v in scenario_flags.items() if not v]
    print(f"    Enabled:  {enabled}")
    print(f"    Disabled: {disabled}")

    print("[4/5] Collecting service endpoints for probing...")
    # Build URLs from discovered services (ClusterIP:port)
    urls = []
    for ns in components.namespaces:
        for svc in ns.services:
            for port in svc.ports:
                url = f"http://{svc.name}.{ns.name}.svc.cluster.local:{port.port}/"
                urls.append(url)

    # Also probe the kubernetes API endpoint directly
    urls.append("https://kubernetes.default.svc.cluster.local:443/healthz")

    print(f"    Discovered {len(urls)} service endpoints")

    probe_results = {}
    if urls:
        print("[5/5] Probing endpoints (best-effort from outside cluster)...")
        probe_results = probe_endpoints(urls, timeout=3)
        reachable = sum(1 for v in probe_results.values() if v)
        print(
            f"    Probed {len(urls)} URLs: {reachable} reachable, "
            f"{len(urls) - reachable} unreachable (expected from outside cluster)"
        )
    else:
        print("[5/5] No service endpoints to probe")

    # Build artifact
    artifact = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "kubeconfig": args.kubeconfig,
        "discovery": discovery_summary,
        "scenario_selection": {
            "flags": scenario_flags,
            "enabled_count": len(enabled),
            "disabled_count": len(disabled),
        },
        "endpoint_probing": {
            "total_urls": len(urls),
            "results": {url: reachable for url, reachable in probe_results.items()},
        },
        "per_namespace_detail": [],
    }

    for ns in components.namespaces:
        ns_detail = {
            "name": ns.name,
            "pods": [
                {"name": p.name, "containers": len(p.containers)} for p in ns.pods
            ],
            "services": [
                {"name": s.name, "ports": [sp.port for sp in s.ports]}
                for s in ns.services
            ],
            "pvcs": [p.name for p in ns.pvcs],
            "vmis": [v.name for v in ns.vmis],
        }
        artifact["per_namespace_detail"].append(ns_detail)

    # Write artifact
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(artifact, f, indent=2)
    print(f"\nArtifact written to: {args.output}")
    print("\nDone. This artifact can be included in the LFX proposal as evidence.")


if __name__ == "__main__":
    main()
