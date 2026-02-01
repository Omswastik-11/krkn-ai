import json
from typing import List, Tuple

from krkn_ai.models.custom_errors import ScenarioParameterInitError
from krkn_ai.utils.rng import rng
from krkn_ai.models.scenario.base import Scenario
from krkn_ai.models.scenario.parameters import (
    EgressParameter,
    IngressParameter,
    InstanceCountParameter,
    NamespaceParameter,
    NetworkChaosNGImageParameter,
    NetworkChaosNGPortsParameter,
    NetworkChaosNGProtocolsParameter,
    NetworkScenarioExecutionParameter,
    NetworkScenarioInterfacesParameter,
    NetworkScenarioNodeNameParameter,
    PodNameParameter,
    PodSelectorParameter,
    TaintParameter,
    TotalChaosDurationParameter,
    NodeSelectorParameter,
)
from krkn_ai.models.cluster_components import Namespace, Pod, Node


class NetworkChaosNGScenario(Scenario):
    name: str = "network-chaos-ng"
    krknctl_name: str = "pod-network-filter"
    krknhub_image: str = "quay.io/krkn-chaos/krkn-hub:pod-network-filter"

    chaos_duration: TotalChaosDurationParameter = TotalChaosDurationParameter()
    namespace: NamespaceParameter = NamespaceParameter()
    pod_selector: PodSelectorParameter = PodSelectorParameter()
    pod_name: PodNameParameter = PodNameParameter()
    node_selector: NodeSelectorParameter = NodeSelectorParameter()
    node_name: NetworkScenarioNodeNameParameter = NetworkScenarioNodeNameParameter()
    instance_count: InstanceCountParameter = InstanceCountParameter()
    execution: NetworkScenarioExecutionParameter = NetworkScenarioExecutionParameter()
    ingress: IngressParameter = IngressParameter(value="false")
    egress: EgressParameter = EgressParameter(value="true")
    interfaces: NetworkScenarioInterfacesParameter = (
        NetworkScenarioInterfacesParameter()
    )
    ports: NetworkChaosNGPortsParameter = NetworkChaosNGPortsParameter()
    protocols: NetworkChaosNGProtocolsParameter = NetworkChaosNGProtocolsParameter()
    image: NetworkChaosNGImageParameter = NetworkChaosNGImageParameter()
    taints: TaintParameter = TaintParameter()

    def __init__(self, **data):
        super().__init__(**data)
        self._scenario_kind = "pod"
        self.mutate()

    @property
    def parameters(self):
        if self._scenario_kind == "node":
            return [
                self.chaos_duration,
                self.node_selector,
                self.node_name,
                self.instance_count,
                self.execution,
                self.ingress,
                self.egress,
                self.interfaces,
                self.ports,
                self.image,
                self.protocols,
                self.taints,
            ]
        return [
            self.chaos_duration,
            self.namespace,
            self.pod_selector,
            self.pod_name,
            self.instance_count,
            self.execution,
            self.ingress,
            self.egress,
            self.interfaces,
            self.ports,
            self.image,
            self.protocols,
            self.taints,
        ]

    def mutate(self):
        pods = [
            (ns, pod) for ns in self._cluster_components.namespaces for pod in ns.pods
        ]
        nodes = self._cluster_components.nodes

        if len(pods) == 0 and len(nodes) == 0:
            raise ScenarioParameterInitError(
                "No pods or nodes found in cluster components for network-chaos-ng scenario"
            )

        if len(pods) > 0 and len(nodes) > 0:
            self._scenario_kind = rng.choice(["pod", "node"])
        elif len(pods) > 0:
            self._scenario_kind = "pod"
        else:
            self._scenario_kind = "node"

        self.execution.mutate()
        self.protocols.value = rng.choice(["tcp", "udp", "tcp,udp"])
        self.ingress.value, self.egress.value = rng.choice(
            [("true", "false"), ("false", "true"), ("true", "true")]
        )

        self._set_ports()

        if self._scenario_kind == "pod":
            self._configure_pod_filter(pods)
        else:
            self._configure_node_filter(nodes)

    def _configure_pod_filter(self, pods: List[Tuple[Namespace, Pod]]):
        self.name = "pod-network-filter"
        self.krknctl_name = "pod-network-filter"
        self.krknhub_image = "quay.io/krkn-chaos/krkn-hub:pod-network-filter"

        ns, pod = rng.choice(pods)
        self.namespace.value = ns.name

        if pod.labels:
            label_key = rng.choice(list(pod.labels.keys()))
            label_value = pod.labels[label_key]
            self.pod_selector.value = f"{label_key}={label_value}"
            self.pod_name.value = ""

            matching_pods = [
                p for p in ns.pods if p.labels.get(label_key) == label_value
            ]
            self.instance_count.value = rng.randint(1, max(1, len(matching_pods)))
        else:
            self.pod_selector.value = ""
            self.pod_name.value = pod.name
            self.instance_count.value = 1

        self.interfaces.value = self._select_interface()
        self.taints.value = "[]"

    def _configure_node_filter(self, nodes: List[Node]):
        self.name = "node-network-filter"
        self.krknctl_name = "node-network-filter"
        self.krknhub_image = "quay.io/krkn-chaos/krkn-hub:node-network-filter"

        nodes_with_labels = [node for node in nodes if node.labels]
        if nodes_with_labels:
            node = rng.choice(nodes_with_labels)
            label_key = rng.choice(list(node.labels.keys()))
            label_value = node.labels[label_key]
            self.node_selector.value = f"{label_key}={label_value}"
            self.node_name.value = ""

            matching_nodes = [
                n for n in nodes if n.labels.get(label_key) == label_value
            ]
            self.instance_count.value = rng.randint(1, max(1, len(matching_nodes)))
            self.taints.value = self._collect_taints(matching_nodes)
        else:
            node = rng.choice(nodes)
            self.node_selector.value = ""
            self.node_name.value = node.name
            self.instance_count.value = 1
            self.taints.value = json.dumps(node.taints) if node.taints else "[]"

        self.interfaces.value = self._select_interface(preferred_node=node)

    def _collect_taints(self, nodes: List[Node]) -> str:
        all_taints = []
        seen = set()
        for node in nodes:
            for taint in node.taints:
                taint_tuple = tuple(sorted(taint.items()))
                if taint_tuple not in seen:
                    seen.add(taint_tuple)
                    all_taints.append(taint)
        return json.dumps(all_taints) if all_taints else "[]"

    def _set_ports(self):
        ports = []
        for namespace in self._cluster_components.namespaces:
            for service in namespace.services:
                for port in service.ports:
                    if port.port:
                        ports.append(str(port.port))

        if ports:
            pick_count = rng.randint(1, min(3, len(ports)))
            # Randomly select ports without using sample
            selected_ports = []
            available_ports = ports.copy()
            for _ in range(pick_count):
                if available_ports:
                    port = rng.choice(available_ports)
                    selected_ports.append(port)
                    available_ports.remove(port)
            self.ports.value = ",".join(selected_ports)
        else:
            self.ports.value = rng.choice(["80", "443", "53", "8080"])

    def _select_interface(self, preferred_node: Node = None) -> str:
        if preferred_node and preferred_node.interfaces:
            return rng.choice(preferred_node.interfaces)

        for node in self._cluster_components.nodes:
            if node.interfaces:
                return rng.choice(node.interfaces)

        return ""
