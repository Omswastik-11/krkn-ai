from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field


class Container(BaseModel):
    name: str
    disabled: bool = False


class Pod(BaseModel):
    name: str
    labels: Dict[str, str] = Field(default_factory=dict)
    containers: List[Container] = Field(default_factory=list)
    disabled: bool = False


class PVC(BaseModel):
    name: str
    labels: Dict[str, str] = Field(default_factory=dict)
    current_usage_percentage: Optional[float] = None
    disabled: bool = False


class ServicePort(BaseModel):
    port: int
    target_port: Optional[Union[int, str]] = None
    protocol: str = "TCP"


class Service(BaseModel):
    name: str
    labels: Dict[str, str] = Field(default_factory=dict)
    ports: List[ServicePort] = Field(default_factory=list)
    disabled: bool = False


class VMI(BaseModel):
    name: str
    disabled: bool = False


class Namespace(BaseModel):
    name: str
    pods: List[Pod] = Field(default_factory=list)
    services: List[Service] = Field(default_factory=list)
    pvcs: List[PVC] = Field(default_factory=list)
    vmis: List[VMI] = Field(default_factory=list)
    disabled: bool = False


class Node(BaseModel):
    name: str
    labels: Dict[str, str] = Field(default_factory=dict)
    free_cpu: float = 0
    free_mem: float = 0
    interfaces: List[str] = Field(default_factory=list)
    taints: List[str] = Field(default_factory=list)
    disabled: bool = False


class ClusterComponents(BaseModel):
    namespaces: List[Namespace] = Field(default_factory=list)
    nodes: List[Node] = Field(default_factory=list)

    def get_active_components(self) -> "ClusterComponents":
        """
        Returns a new ClusterComponents instance with disabled items filtered out.
        This provides a centralized way to filter disabled components for all scenarios.
        """
        active_namespaces = []
        for ns in self.namespaces:
            if ns.disabled:
                continue
            # Create a copy of namespace with filtered sub-components
            active_ns = Namespace(
                name=ns.name,
                pods=[p for p in ns.pods if not p.disabled],
                services=[s for s in ns.services if not s.disabled],
                pvcs=[pvc for pvc in ns.pvcs if not pvc.disabled],
                vmis=[vmi for vmi in ns.vmis if not vmi.disabled],
                disabled=ns.disabled,
            )
            active_namespaces.append(active_ns)

        active_nodes = [n for n in self.nodes if not n.disabled]

        return ClusterComponents(namespaces=active_namespaces, nodes=active_nodes)
