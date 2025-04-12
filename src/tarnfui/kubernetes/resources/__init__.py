"""Resources package for Kubernetes resource handlers.

This package contains specialized handlers for different Kubernetes resource types.
"""

from tarnfui.kubernetes.resources.deployments import DeploymentResource
from tarnfui.kubernetes.resources.events import (
    EVENT_COMPONENT,
    EVENT_REASON_STARTED,
    EVENT_REASON_STOPPED,
    EVENT_TYPE_NORMAL,
    EVENT_TYPE_WARNING,
    create_scaling_event,
)

__all__ = [
    "DeploymentResource",
    "create_scaling_event",
    "EVENT_TYPE_NORMAL",
    "EVENT_TYPE_WARNING",
    "EVENT_REASON_STOPPED",
    "EVENT_REASON_STARTED",
    "EVENT_COMPONENT",
]
