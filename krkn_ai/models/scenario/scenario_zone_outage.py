from typing import List
from krkn_ai.models.scenario.base import Scenario
from krkn_ai.models.scenario.parameters import (
    CloudTypeParameter,
    DurationParameter,
    VpcIdParameter,
    SubnetIdParameter,
    ZoneParameter,
    KubeCheckParameter,
)
from krkn_ai.utils.rng import rng


class ZoneOutageScenario(Scenario):
    """Scenario for simulating zone outages in cloud environments like AWS or GCP."""

    name: str = "zone_outages"
    krknctl_name: str = "zone-outages"
    krknhub_image: str = "quay.io/krkn-chaos/krkn-hub:zone-outages"

    cloud_type: CloudTypeParameter = CloudTypeParameter()
    duration: DurationParameter = DurationParameter()
    vpc_id: VpcIdParameter = VpcIdParameter()
    subnet_id: SubnetIdParameter = SubnetIdParameter()
    zone: ZoneParameter = ZoneParameter()
    kube_check: KubeCheckParameter = KubeCheckParameter()

    def __init__(self, **data):
        super().__init__(**data)
        self.mutate()

    @property
    def parameters(self):
        return [
            self.cloud_type,
            self.duration,
            self.vpc_id,
            self.subnet_id,
            self.zone,
            self.kube_check,
        ]

    def mutate(self):
        # Randomly select cloud type initially
        self.cloud_type.mutate()

        # Try to detect actual cloud from node labels
        detected_cloud = self._detect_cloud_type()
        if detected_cloud:
            self.cloud_type.value = detected_cloud

        # Configure parameters based on cloud type
        if self.cloud_type.value == "gcp":
            zones = self._get_zones_from_nodes()
            self.zone.value = rng.choice(zones) if zones else "us-west1-a"
            self.vpc_id.value = ""
            self.subnet_id.value = []

        elif self.cloud_type.value == "aws":
            self.vpc_id.value = "vpc-xxxxxx"  # Placeholder for real VPC
            self.subnet_id.value = ["subnet-xxxxxx"]  # Placeholder for subnets
            self.zone.value = ""
            self.kube_check.value = True

    def _detect_cloud_type(self) -> str:
        """Infer cloud provider from node labels."""
        for node in self._cluster_components.nodes:
            labels = node.labels
            if any(k.startswith("cloud.google.com/") for k in labels.keys()):
                return "gcp"
        return ""

    def _get_zones_from_nodes(self) -> List[str]:
        """Extract unique zones from node labels."""
        zones = set()
        for node in self._cluster_components.nodes:
            for label in [
                "failure-domain.beta.kubernetes.io/zone",
                "topology.kubernetes.io/zone",
            ]:
                if label in node.labels:
                    zones.add(node.labels[label])
        return list(zones)
