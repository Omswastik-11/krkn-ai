from krkn_ai.models.custom_errors import ScenarioParameterInitError
from krkn_ai.utils.rng import rng
from krkn_ai.models.scenario.base import Scenario
from krkn_ai.models.scenario.parameters import (
    ServiceDisruptionNamespaceParameter,
    ServiceDisruptionLabelSelectorParameter,
    ServiceDisruptionDeleteCountParameter,
    ServiceDisruptionRunsParameter,
)


class ServiceDisruptionScenario(Scenario):
    name: str = "service-disruption-scenarios"
    krknctl_name: str = "service-disruption-scenarios"
    krknhub_image: str = "quay.io/krkn-chaos/krkn-hub:service-disruption-scenarios"

    namespace: ServiceDisruptionNamespaceParameter = (
        ServiceDisruptionNamespaceParameter()
    )
    label_selector: ServiceDisruptionLabelSelectorParameter = (
        ServiceDisruptionLabelSelectorParameter()
    )
    delete_count: ServiceDisruptionDeleteCountParameter = (
        ServiceDisruptionDeleteCountParameter()
    )
    runs: ServiceDisruptionRunsParameter = ServiceDisruptionRunsParameter()

    def __init__(self, **data):
        super().__init__(**data)
        self.mutate()

    @property
    def parameters(self):
        params = [
            self.delete_count,
            self.runs,
        ]

        if self.namespace.value:
            params.insert(0, self.namespace)
        else:
            params.insert(0, self.label_selector)

        return params

    def mutate(self):
        namespaces = self._cluster_components.namespaces

        if len(namespaces) == 0:
            raise ScenarioParameterInitError(
                "No namespaces found in cluster components"
            )

        namespace = rng.choice(namespaces)
        self.namespace.value = namespace.name
        self.label_selector.value = ""
