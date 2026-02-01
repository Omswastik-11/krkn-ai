from krkn_ai.models.custom_errors import ScenarioParameterInitError
from krkn_ai.utils.rng import rng
from krkn_ai.models.scenario.base import Scenario
from krkn_ai.models.scenario.parameters import (
    ServiceHijackingServiceNameParameter,
    ServiceHijackingServiceNamespaceParameter,
    ServiceHijackingTargetPortParameter,
    ServiceHijackingImageParameter,
    ServiceHijackingChaosDurationParameter,
    ServiceHijackingPrivilegedParameter,
    ServiceHijackingScenarioFilePathParameter,
)


class ServiceHijackingScenario(Scenario):
    name: str = "service-hijacking"
    krknctl_name: str = "service-hijacking"
    krknhub_image: str = "quay.io/krkn-chaos/krkn-hub:service-hijacking"

    service_name: ServiceHijackingServiceNameParameter = (
        ServiceHijackingServiceNameParameter()
    )
    service_namespace: ServiceHijackingServiceNamespaceParameter = (
        ServiceHijackingServiceNamespaceParameter()
    )
    service_target_port: ServiceHijackingTargetPortParameter = (
        ServiceHijackingTargetPortParameter()
    )
    image: ServiceHijackingImageParameter = ServiceHijackingImageParameter()
    chaos_duration: ServiceHijackingChaosDurationParameter = (
        ServiceHijackingChaosDurationParameter()
    )
    privileged: ServiceHijackingPrivilegedParameter = (
        ServiceHijackingPrivilegedParameter()
    )
    scenario_file_path: ServiceHijackingScenarioFilePathParameter = (
        ServiceHijackingScenarioFilePathParameter()
    )

    def __init__(self, **data):
        super().__init__(**data)
        self.mutate()

    @property
    def parameters(self):
        return [
            self.service_name,
            self.service_namespace,
            self.service_target_port,
            self.image,
            self.chaos_duration,
            self.privileged,
            self.scenario_file_path,
        ]

    def mutate(self):
        services = []
        for ns in self._cluster_components.namespaces:
            for svc in ns.services:
                services.append((ns.name, svc))

        if len(services) == 0:
            raise ScenarioParameterInitError("No services found in cluster components")

        namespace_name, service = rng.choice(services)

        self.service_namespace.value = namespace_name
        self.service_name.value = service.name

        if service.ports:
            port = rng.choice(service.ports)
            self.service_target_port.value = str(port.port)
        else:
            self.service_target_port.value = "80"

        self.scenario_file_path.value = ""
