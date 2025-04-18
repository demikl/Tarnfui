"""Kubernetes events handling module.

This module provides functions for creating events for Kubernetes resources.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from kubernetes import client

from tarnfui.kubernetes.connection import KubernetesConnection

logger = logging.getLogger(__name__)

# Constants for event types
EVENT_TYPE_NORMAL = "Normal"
EVENT_TYPE_WARNING = "Warning"

# Constants for event reasons
EVENT_REASON_STOPPED = "Stopped"
EVENT_REASON_STARTED = "Started"
EVENT_REASON_SUSPENDED = "Suspended"
EVENT_REASON_RESTORED = "Restored"

# Constants for event actions
EVENT_ACTION_SUSPENSION = "Suspension"
EVENT_ACTION_RESTORATION = "Restoration"

# Component name for events
EVENT_COMPONENT = "tarnfui"


def create_suspension_event(
    connection: KubernetesConnection,
    resource: Any,
    api_version: str,
    kind: str,
    message: str,
) -> None:
    """Create a Kubernetes event for a resource suspension operation.

    Args:
        connection: The Kubernetes connection to use
        resource: The resource object that was suspended
        api_version: API version of the resource
        kind: Resource kind
        message: Detailed message for the event
    """
    _create_event(
        connection=connection,
        resource=resource,
        api_version=api_version,
        kind=kind,
        event_type=EVENT_TYPE_NORMAL,
        reason=EVENT_REASON_SUSPENDED,
        message=message,
        action=EVENT_ACTION_SUSPENSION,
    )


def create_restoration_event(
    connection: KubernetesConnection,
    resource: Any,
    api_version: str,
    kind: str,
    message: str,
) -> None:
    """Create a Kubernetes event for a resource restoration operation.

    Args:
        connection: The Kubernetes connection to use
        resource: The resource object that was restored
        api_version: API version of the resource
        kind: Resource kind
        message: Detailed message for the event
    """
    _create_event(
        connection=connection,
        resource=resource,
        api_version=api_version,
        kind=kind,
        event_type=EVENT_TYPE_NORMAL,
        reason=EVENT_REASON_RESTORED,
        message=message,
        action=EVENT_ACTION_RESTORATION,
    )


def _create_event(
    connection: KubernetesConnection,
    resource: Any,
    api_version: str,
    kind: str,
    event_type: str,
    reason: str,
    message: str,
    action: str,
) -> None:
    """Create a Kubernetes event for a resource operation.

    Args:
        connection: The Kubernetes connection to use
        resource: The resource object to create an event for
        api_version: API version of the resource
        kind: Resource kind
        event_type: Type of event (Normal or Warning)
        reason: Short reason for the event
        message: Detailed message for the event
        action: Action being performed (Scaling, Suspension, Restoration)
    """
    try:
        # Get resource metadata
        name = ""
        namespace = ""
        uid = None

        if hasattr(resource, "metadata"):
            metadata = resource.metadata
            name = metadata.name if hasattr(metadata, "name") else ""
            namespace = metadata.namespace if hasattr(metadata, "namespace") else ""
            uid = metadata.uid if hasattr(metadata, "uid") else None
        elif isinstance(resource, dict) and "metadata" in resource:
            metadata = resource["metadata"]
            name = metadata.get("name", "")
            namespace = metadata.get("namespace", "")
            uid = metadata.get("uid")

        if not name or not namespace:
            logger.warning(f"Cannot create event for {kind} without name and namespace")
            return

        # Use datetime with timezone info
        now = datetime.now(UTC)

        # Initialize the event body
        body = client.EventsV1Event(
            metadata=client.V1ObjectMeta(generate_name=f"{name}-", namespace=namespace),
            reason=reason,
            note=message,
            type=event_type,
            reporting_controller=EVENT_COMPONENT,
            reporting_instance=connection.hostname,
            action=action,
            regarding=client.V1ObjectReference(
                api_version=api_version, kind=kind, name=name, namespace=namespace, uid=uid
            ),
            event_time=now,
        )

        # Create the event in the Kubernetes API
        connection.events_v1_api.create_namespaced_event(namespace=namespace, body=body)
        logger.debug(f"Created event for {kind} {namespace}/{name}: {reason}")

    except Exception as e:
        logger.warning(f"Failed to create event for {kind} {namespace}/{name}: {e}")
