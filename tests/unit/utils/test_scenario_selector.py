"""
Unit tests for krkn_ai.utils.scenario_selector

Verifies that scenario enable/disable flags are correctly derived
from different ClusterComponents configurations.
"""

from krkn_ai.models.cluster_components import (
    ClusterComponents,
    Container,
    Namespace,
    Node,
    Pod,
    PVC,
    Service,
    ServicePort,
    VMI,
)
from krkn_ai.utils.scenario_selector import select_scenarios


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ns(pods=None, services=None, pvcs=None, vmis=None) -> Namespace:
    return Namespace(
        name="test-ns",
        pods=pods or [],
        services=services or [],
        pvcs=pvcs or [],
        vmis=vmis or [],
    )


def _components(
    pods=None, services=None, pvcs=None, vmis=None, nodes=None
) -> ClusterComponents:
    return ClusterComponents(
        namespaces=[_ns(pods=pods, services=services, pvcs=pvcs, vmis=vmis)],
        nodes=nodes or [],
    )


def _pod(num_containers: int = 1) -> Pod:
    return Pod(
        name="app-pod",
        labels={"app": "test"},
        containers=[Container(name=f"c{i}") for i in range(num_containers)],
    )


def _node(interfaces=None) -> Node:
    return Node(
        name="node-1",
        labels={"kubernetes.io/os": "linux"},
        free_cpu=4.0,
        free_mem=8.0,
        interfaces=interfaces or [],
    )


# ---------------------------------------------------------------------------
# Pod-based scenarios
# ---------------------------------------------------------------------------


class TestPodScenarios:
    def test_enabled_when_pods_exist(self):
        flags = select_scenarios(_components(pods=[_pod()]))
        assert flags["pod-scenarios"] is True

    def test_disabled_when_no_pods(self):
        flags = select_scenarios(_components())
        assert flags["pod-scenarios"] is False

    def test_dns_outage_enabled_with_pods(self):
        flags = select_scenarios(_components(pods=[_pod()]))
        assert flags["dns-outage"] is True

    def test_dns_outage_disabled_without_pods(self):
        flags = select_scenarios(_components())
        assert flags["dns-outage"] is False


# ---------------------------------------------------------------------------
# Container scenarios
# ---------------------------------------------------------------------------


class TestContainerScenarios:
    def test_enabled_when_multi_container_pod_exists(self):
        flags = select_scenarios(_components(pods=[_pod(num_containers=2)]))
        assert flags["container-scenarios"] is True

    def test_disabled_when_single_container_pods_only(self):
        flags = select_scenarios(_components(pods=[_pod(num_containers=1)]))
        assert flags["container-scenarios"] is False

    def test_disabled_when_no_pods(self):
        flags = select_scenarios(_components())
        assert flags["container-scenarios"] is False


# ---------------------------------------------------------------------------
# Service-based scenarios
# ---------------------------------------------------------------------------


class TestServiceScenarios:
    def test_application_outages_enabled_with_services(self):
        svc = Service(name="svc", labels={}, ports=[ServicePort(port=80)])
        flags = select_scenarios(_components(services=[svc]))
        assert flags["application-outages"] is True

    def test_application_outages_disabled_without_services(self):
        flags = select_scenarios(_components())
        assert flags["application-outages"] is False


# ---------------------------------------------------------------------------
# Node-based scenarios
# ---------------------------------------------------------------------------


class TestNodeScenarios:
    def test_hog_scenarios_enabled_with_nodes(self):
        flags = select_scenarios(_components(nodes=[_node()]))
        assert flags["node-cpu-hog"] is True
        assert flags["node-memory-hog"] is True
        assert flags["node-io-hog"] is True
        assert flags["time-scenarios"] is True

    def test_hog_scenarios_disabled_without_nodes(self):
        flags = select_scenarios(_components())
        assert flags["node-cpu-hog"] is False
        assert flags["node-memory-hog"] is False
        assert flags["node-io-hog"] is False
        assert flags["time-scenarios"] is False

    def test_network_scenarios_enabled_with_interfaces(self):
        flags = select_scenarios(_components(nodes=[_node(interfaces=["eth0"])]))
        assert flags["network-scenarios"] is True
        assert flags["syn-flood"] is True

    def test_network_scenarios_disabled_without_interfaces(self):
        flags = select_scenarios(_components(nodes=[_node(interfaces=[])]))
        assert flags["network-scenarios"] is False
        assert flags["syn-flood"] is False


# ---------------------------------------------------------------------------
# PVC scenarios
# ---------------------------------------------------------------------------


class TestPVCScenarios:
    def test_enabled_when_pvcs_exist(self):
        flags = select_scenarios(_components(pvcs=[PVC(name="pvc-1")]))
        assert flags["pvc-scenarios"] is True

    def test_disabled_without_pvcs(self):
        flags = select_scenarios(_components())
        assert flags["pvc-scenarios"] is False


# ---------------------------------------------------------------------------
# KubeVirt scenarios
# ---------------------------------------------------------------------------


class TestKubevirtScenarios:
    def test_enabled_when_vmis_exist(self):
        flags = select_scenarios(_components(vmis=[VMI(name="vm-a")]))
        assert flags["kubevirt-scenarios"] is True

    def test_disabled_without_vmis(self):
        flags = select_scenarios(_components())
        assert flags["kubevirt-scenarios"] is False


# ---------------------------------------------------------------------------
# Full-cluster and empty-cluster edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_all_scenarios_enabled_for_full_cluster(self):
        c = ClusterComponents(
            namespaces=[
                Namespace(
                    name="prod",
                    pods=[_pod(num_containers=2)],
                    services=[
                        Service(name="svc", labels={}, ports=[ServicePort(port=80)])
                    ],
                    pvcs=[PVC(name="pvc-1")],
                    vmis=[VMI(name="vm-a")],
                )
            ],
            nodes=[_node(interfaces=["eth0"])],
        )
        flags = select_scenarios(c)
        disabled = [k for k, v in flags.items() if not v]
        assert not disabled, (
            f"Expected all scenarios enabled but got disabled: {disabled}"
        )

    def test_empty_cluster_disables_all(self):
        flags = select_scenarios(ClusterComponents(namespaces=[], nodes=[]))
        enabled = [k for k, v in flags.items() if v]
        assert not enabled, f"Expected all disabled but got enabled: {enabled}"
