"""
Derives per-scenario enable/disable flags from discovered cluster components.

Used by the template generator so the emitted krkn-ai.yaml only enables
scenarios that actually apply to the target infrastructure — reducing
noise and preventing runs that would fail validation in ScenarioFactory.
"""

from typing import Dict

from krkn_ai.models.cluster_components import ClusterComponents
from krkn_ai.utils.logger import get_logger

logger = get_logger(__name__)


def select_scenarios(components: ClusterComponents) -> Dict[str, bool]:
    """Return a scenario-name -> enabled mapping based on what was discovered.

    Rules applied
    -------------
    pod-scenarios          pods found in any namespace
    container-scenarios    at least one pod with more than one container
    application-outages    services found (needed for network blocking)
    node-cpu-hog           at least one schedulable node
    node-memory-hog        at least one schedulable node
    node-io-hog            at least one schedulable node
    time-scenarios         at least one schedulable node
    network-scenarios      at least one node exposes a network interface
    dns-outage             pods found (DNS used by all pods)
    syn-flood              at least one node with network interfaces
    pvc-scenarios          PVCs found in any namespace
    kubevirt-scenarios     VirtualMachineInstances found in any namespace

    Args:
        components: ClusterComponents returned by ClusterManager.

    Returns:
        Dict mapping each scenario YAML key to a bool enable flag.
    """
    namespaces = components.namespaces
    nodes = components.nodes

    has_pods = any(ns.pods for ns in namespaces)
    has_multi_container_pod = any(
        len(pod.containers) > 1 for ns in namespaces for pod in ns.pods
    )
    has_services = any(ns.services for ns in namespaces)
    has_pvcs = any(ns.pvcs for ns in namespaces)
    has_vmis = any(ns.vmis for ns in namespaces)
    has_nodes = len(nodes) > 0
    has_interfaces = any(n.interfaces for n in nodes)

    flags: Dict[str, bool] = {
        "pod-scenarios": has_pods,
        "container-scenarios": has_multi_container_pod,
        "application-outages": has_services,
        "node-cpu-hog": has_nodes,
        "node-memory-hog": has_nodes,
        "node-io-hog": has_nodes,
        "time-scenarios": has_nodes,
        "network-scenarios": has_interfaces,
        "dns-outage": has_pods,
        "syn-flood": has_interfaces,
        "pvc-scenarios": has_pvcs,
        "kubevirt-scenarios": has_vmis,
    }

    enabled = [k for k, v in flags.items() if v]
    disabled = [k for k, v in flags.items() if not v]
    logger.debug("Scenarios ENABLED  (%d): %s", len(enabled), enabled)
    logger.debug("Scenarios DISABLED (%d): %s", len(disabled), disabled)

    return flags
