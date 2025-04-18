"""Resources package for Kubernetes resource handlers.

This package contains specialized handlers for different Kubernetes resource types.
"""

from tarnfui.kubernetes.resources.events import (
    create_restoration_event,
    create_suspension_event,
)

__all__ = [
    "create_suspension_event",
    "create_restoration_event",
]
