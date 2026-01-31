"""
Pod Network Chaos Scenarios for krkn-ai.

This scenario injects network chaos into pods by applying network filters
to disrupt ingress and/or egress traffic. It differs from the general
network-chaos scenario which targets nodes.

Supported disruptions:
- Block ingress traffic to pods
- Block egress traffic from pods
- Block specific ports
"""

from collections import Counter
from typing import List, Tuple

from krkn_ai.models.cluster_components import Namespace, Pod
from krkn_ai.models.custom_errors import ScenarioParameterInitError
from krkn_ai.models.scenario.base import Scenario
from krkn_ai.models.scenario.parameters import (
    PodNetworkNamespaceParameter,
    PodNetworkImageParameter,
    PodNetworkLabelSelectorParameter,
    PodNetworkExcludeLabelParameter,
    PodNetworkPodNameParameter,
    PodNetworkInstanceCountParameter,
    PodNetworkTrafficTypeParameter,
    PodNetworkIngressPortsParameter,
    PodNetworkEgressPortsParameter,
    PodNetworkWaitDurationParameter,
    PodNetworkTestDurationParameter,
)
from krkn_ai.utils.rng import rng


class PodNetworkChaosScenario(Scenario):
    """
    Pod Network Chaos Scenario class for network disruption at the pod level.

    This scenario targets Kubernetes pods and injects network chaos by
    applying filters to block or disrupt ingress/egress traffic.
    """

    name: str = "pod-network-chaos"
    krknctl_name: str = "pod-network-chaos"
    krknhub_image: str = (
        "containers.krkn-chaos.dev/krkn-chaos/krkn-hub:pod-network-chaos"
    )

    namespace: PodNetworkNamespaceParameter = PodNetworkNamespaceParameter()
    image: PodNetworkImageParameter = PodNetworkImageParameter()
    label_selector: PodNetworkLabelSelectorParameter = (
        PodNetworkLabelSelectorParameter()
    )
    exclude_label: PodNetworkExcludeLabelParameter = PodNetworkExcludeLabelParameter()
    pod_name: PodNetworkPodNameParameter = PodNetworkPodNameParameter()
    instance_count: PodNetworkInstanceCountParameter = (
        PodNetworkInstanceCountParameter()
    )
    traffic_type: PodNetworkTrafficTypeParameter = PodNetworkTrafficTypeParameter()
    ingress_ports: PodNetworkIngressPortsParameter = PodNetworkIngressPortsParameter()
    egress_ports: PodNetworkEgressPortsParameter = PodNetworkEgressPortsParameter()
    wait_duration: PodNetworkWaitDurationParameter = PodNetworkWaitDurationParameter()
    test_duration: PodNetworkTestDurationParameter = PodNetworkTestDurationParameter()

    def __init__(self, **data):
        super().__init__(**data)
        self.mutate()

    @property
    def parameters(self):
        return [
            self.namespace,
            self.image,
            self.label_selector,
            self.exclude_label,
            self.pod_name,
            self.instance_count,
            self.traffic_type,
            self.ingress_ports,
            self.egress_ports,
            self.wait_duration,
            self.test_duration,
        ]

    def mutate(self) -> None:
        namespace_pod_tuples: List[Tuple[Namespace, Pod]] = []

        for namespace in self._cluster_components.namespaces:
            for pod in namespace.pods:
                if len(pod.labels) > 0:
                    namespace_pod_tuples.append((namespace, pod))

        if len(namespace_pod_tuples) == 0:
            raise ScenarioParameterInitError(
                "No pods found with labels for pod-network-chaos scenario"
            )

        use_pod_name = rng.random() < 0.5

        if use_pod_name:
            self._select_by_pod_name(namespace_pod_tuples)
        else:
            self._select_by_label(namespace_pod_tuples)

        self.traffic_type.mutate()
        self.test_duration.mutate()

        self.wait_duration.value = self.test_duration.value * 2 + rng.randint(0, 60)

        self._set_port_filters()

    def _select_by_pod_name(
        self, namespace_pod_tuples: List[Tuple[Namespace, Pod]]
    ) -> None:
        """Select a specific pod by name."""
        namespace, pod = rng.choice(namespace_pod_tuples)
        self.namespace.value = namespace.name
        self.pod_name.value = pod.name
        self.label_selector.value = ""
        self.instance_count.value = 1

    def _select_by_label(
        self, namespace_pod_tuples: List[Tuple[Namespace, Pod]]
    ) -> None:
        """Select pods by label selector."""
        namespace_pods: dict = {}
        for namespace, pod in namespace_pod_tuples:
            if namespace.name not in namespace_pods:
                namespace_pods[namespace.name] = []
            namespace_pods[namespace.name].append(pod)

        namespace_name = rng.choice(list(namespace_pods.keys()))
        pods = namespace_pods[namespace_name]
        self.namespace.value = namespace_name

        all_labels: Counter = Counter()
        for pod in pods:
            for label, value in pod.labels.items():
                all_labels[f"{label}={value}"] += 1

        if len(all_labels) == 0:
            pod = rng.choice(pods)
            self.pod_name.value = pod.name
            self.label_selector.value = ""
            self.instance_count.value = 1
            return

        label = rng.choice(list(all_labels.keys()))
        if "=" in label:
            key, value = label.split("=", 1)
            self.label_selector.value = f"{key}={value}"
        else:
            self.label_selector.value = label

        matching_count = all_labels[label]
        self.instance_count.mutate(max_count=matching_count)
        self.pod_name.value = ""

    def _set_port_filters(self) -> None:
        """Optionally set ingress/egress port filters."""
        traffic_type = self.traffic_type.value

        if rng.random() < 0.5:
            common_ports = [80, 443, 8080, 8443, 3000, 5000, 6379, 5432, 3306, 27017]

            if "ingress" in traffic_type.lower():
                num_ports = rng.randint(1, 3)
                selected_ports = []
                for _ in range(num_ports):
                    port = rng.choice(common_ports)
                    if port not in selected_ports:
                        selected_ports.append(port)
                if selected_ports:
                    self.ingress_ports.value = (
                        "[" + ",".join(map(str, selected_ports)) + "]"
                    )

            if "egress" in traffic_type.lower():
                num_ports = rng.randint(1, 3)
                selected_ports = []
                for _ in range(num_ports):
                    port = rng.choice(common_ports)
                    if port not in selected_ports:
                        selected_ports.append(port)
                if selected_ports:
                    self.egress_ports.value = (
                        "[" + ",".join(map(str, selected_ports)) + "]"
                    )
