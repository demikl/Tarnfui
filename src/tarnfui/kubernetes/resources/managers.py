"""Resource Manager implementation for Kubernetes resources.

This module provides implementations of ResourceManager for resources that can
manage other Kubernetes workloads.
"""

# Import managers from their dedicated modules
from tarnfui.kubernetes.resources.managers import Kustomization

__all__ = [
    "Kustomization",
]
