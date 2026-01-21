from enum import Enum
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator


class Container(BaseModel):
    name: str
    is_disabled: bool = False  # When True, exclude this container from chaos testing


class Pod(BaseModel):
    name: str
    labels: Dict[str, str] = {}
    containers: List[Container] = []
    is_disabled: bool = False  # When True, exclude this pod from chaos testing


class PVC(BaseModel):
    name: str
    labels: Dict[str, str] = {}
    current_usage_percentage: Optional[float] = None
    is_disabled: bool = False  # When True, exclude this PVC from chaos testing


class ServicePort(BaseModel):
    port: int
    target_port: Optional[Union[int, str]] = None
    protocol: str = "TCP"


class Service(BaseModel):
    name: str
    labels: Dict[str, str] = {}
    ports: List[ServicePort] = []
    is_disabled: bool = False  # When True, exclude this service from chaos testing


class VMI(BaseModel):
    name: str
    is_disabled: bool = False  # When True, exclude this VMI from chaos testing


class Namespace(BaseModel):
    name: str
    pods: List[Pod] = []
    services: List[Service] = []
    pvcs: List[PVC] = []
    vmis: List[VMI] = []
    is_disabled: bool = False  # When True, exclude this namespace from chaos testing


class Node(BaseModel):
    name: str
    labels: Dict[str, str] = {}
    free_cpu: float = 0
    free_mem: float = 0
    interfaces: List[str] = []
    taints: List[str] = []
    is_disabled: bool = False  # When True, exclude this node from chaos testing


class ClusterComponents(BaseModel):
    namespaces: List[Namespace] = []
    nodes: List[Node] = []
