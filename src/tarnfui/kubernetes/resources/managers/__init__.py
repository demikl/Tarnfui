"""Resource managers package.

This package contains implementations of ResourceManager for specialized
Kubernetes resources that can manage other resources.
"""

from tarnfui.kubernetes.resources.managers.kustomization import Kustomization

__all__ = [
    "Kustomization",
]
