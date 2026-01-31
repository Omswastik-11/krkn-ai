"""
Node Scenarios for krkn-ai.

This scenario performs infrastructure-level node operations such as:
- Stopping/starting nodes
- Rebooting nodes
- Terminating nodes
- Stopping/starting kubelet
- Crashing nodes

Supports multiple cloud providers: AWS, GCP, Azure, VMware, IBM Cloud, and Baremetal.
"""

from collections import Counter
from typing import List

from krkn_ai.models.cluster_components import Node
from krkn_ai.models.custom_errors import ScenarioParameterInitError
from krkn_ai.models.scenario.base import Scenario
from krkn_ai.models.scenario.parameters import (
    NodeScenarioActionParameter,
    NodeScenarioCloudTypeParameter,
    NodeScenarioDurationParameter,
    NodeScenarioExcludeLabelParameter,
    NodeScenarioInstanceCountParameter,
    NodeScenarioKubeCheckParameter,
    NodeScenarioLabelSelectorParameter,
    NodeScenarioNodeNameParameter,
    NodeScenarioRunsParameter,
    NodeScenarioTimeoutParameter,
)
from krkn_ai.utils.rng import rng


class NodeScenario(Scenario):
    """
    Node Scenario class for infrastructure-level chaos testing.

    This scenario targets Kubernetes nodes and performs various actions
    such as stopping, starting, rebooting, or terminating nodes.
    It can also manipulate the kubelet service on nodes.
    """

    name: str = "node-scenarios"
    krknctl_name: str = "node-scenarios"
    krknhub_image: str = "containers.krkn-chaos.dev/krkn-chaos/krkn-hub:node-scenarios"

    action: NodeScenarioActionParameter = NodeScenarioActionParameter()
    label_selector: NodeScenarioLabelSelectorParameter = (
        NodeScenarioLabelSelectorParameter()
    )
    exclude_label: NodeScenarioExcludeLabelParameter = (
        NodeScenarioExcludeLabelParameter()
    )
    node_name: NodeScenarioNodeNameParameter = NodeScenarioNodeNameParameter()
    instance_count: NodeScenarioInstanceCountParameter = (
        NodeScenarioInstanceCountParameter()
    )
    runs: NodeScenarioRunsParameter = NodeScenarioRunsParameter()
    cloud_type: NodeScenarioCloudTypeParameter = NodeScenarioCloudTypeParameter()
    kube_check: NodeScenarioKubeCheckParameter = NodeScenarioKubeCheckParameter()
    timeout: NodeScenarioTimeoutParameter = NodeScenarioTimeoutParameter()
    duration: NodeScenarioDurationParameter = NodeScenarioDurationParameter()

    def __init__(self, **data):
        super().__init__(**data)
        self.mutate()

    @property
    def parameters(self):
        return [
            self.action,
            self.label_selector,
            self.exclude_label,
            self.node_name,
            self.instance_count,
            self.runs,
            self.cloud_type,
            self.kube_check,
            self.timeout,
            self.duration,
        ]

    def mutate(self):
        nodes = self._cluster_components.nodes

        if len(nodes) == 0:
            raise ScenarioParameterInitError(
                "No nodes found in cluster components for node-scenarios"
            )

        # Filter out nodes with exclude_label if specified
        if self.exclude_label.value:
            nodes = [
                node for node in nodes if self.exclude_label.value not in node.labels
            ]

        if len(nodes) == 0:
            raise ScenarioParameterInitError(
                "No eligible nodes found after applying exclude_label filter"
            )

        all_node_labels = Counter()
        for node in nodes:
            for label, value in node.labels.items():
                all_node_labels[f"{label}={value}"] += 1

        # Decide between targeting by node name or by label selector
        use_node_name = rng.random() < 0.5 or len(all_node_labels) == 0

        if use_node_name:
            self._select_by_node_name(nodes)
        else:
            self._select_by_label(nodes, all_node_labels)

        # Detect cloud type from nodes
        self.cloud_type.value = self._detect_cloud_type(nodes)

        self.action.mutate(cloud_type=self.cloud_type.value)
        self.runs.mutate()
        self.timeout.mutate()
        self.duration.mutate()

    def _select_by_node_name(self, nodes: List[Node]):
        # Select 1-3 random nodes (or all if fewer available)
        num_nodes = rng.randint(1, min(3, len(nodes)) + 1)

        # Shuffle and select the first num_nodes
        shuffled_indices = list(range(len(nodes)))
        rng.rng.shuffle(shuffled_indices)
        selected_nodes = [nodes[i] for i in shuffled_indices[:num_nodes]]

        self.node_name.value = ",".join([node.name for node in selected_nodes])
        self.instance_count.value = len(selected_nodes)
        self.label_selector.value = ""

    def _select_by_label(self, nodes: List[Node], all_node_labels: Counter):
        label = rng.choice(list(all_node_labels.keys()))

        if "=" in label:
            key, value = label.split("=", 1)
            # if value is empty or common patterns, use key only
            if value in ["", "true", "True"]:
                self.label_selector.value = key
            else:
                self.label_selector.value = f"{key}={value}"
        else:
            self.label_selector.value = label

        matching_count = all_node_labels[label]
        self.instance_count.mutate(max_count=matching_count)
        self.node_name.value = ""

    def _detect_cloud_type(self, nodes: List[Node]) -> str:
        for node in nodes:
            labels = node.labels

            # Check for AWS indicators
            if any("eks" in str(v).lower() for v in labels.values()):
                return "aws"
            if any("aws" in str(v).lower() for v in labels.values()):
                return "aws"

            # Check for GCP indicators
            if any("gke" in str(v).lower() for v in labels.values()):
                return "gcp"
            if any("gcp" in str(v).lower() for v in labels.values()):
                return "gcp"

            # Check for Azure indicators
            if any("aks" in str(v).lower() for v in labels.values()):
                return "azure"
            if any("azure" in str(v).lower() for v in labels.values()):
                return "azure"

            # Check for OpenShift/VMware indicators
            if any("vmware" in str(v).lower() for v in labels.values()):
                return "vmware"

            # Check for IBM Cloud indicators
            if any("ibm" in str(v).lower() for v in labels.values()):
                return "ibmcloud"

        # Default to baremetal if no specific cloud detected
        return "bm"
