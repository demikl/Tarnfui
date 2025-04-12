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

# Component name for events
EVENT_COMPONENT = "tarnfui"


def create_scaling_event(
    connection: KubernetesConnection,
    resource: Any,
    api_version: str,
    kind: str,
    event_type: str,
    reason: str,
    message: str
) -> None:
    """Create a Kubernetes event for a resource scaling operation.

    Args:
        connection: The Kubernetes connection to use
        resource: The resource object to create an event for
        api_version: API version of the resource
        kind: Resource kind
        event_type: Type of event (Normal or Warning)
        reason: Short reason for the event
        message: Detailed message for the event
    """
    try:
        # Get resource metadata
        name = ""
        namespace = ""
        uid = None

        if hasattr(resource, "metadata"):
            metadata = resource.metadata
            name = metadata.name if hasattr(metadata, "name") else ""
            namespace = metadata.namespace if hasattr(
                metadata, "namespace") else ""
            uid = metadata.uid if hasattr(metadata, "uid") else None
        elif isinstance(resource, dict) and "metadata" in resource:
            metadata = resource["metadata"]
            name = metadata.get("name", "")
            namespace = metadata.get("namespace", "")
            uid = metadata.get("uid")

        if not name or not namespace:
            logger.warning(
                f"Cannot create event for {kind} without name and namespace")
            return

        # Use datetime with timezone info
        now = datetime.now(UTC)

        # Initialize the event body
        body = client.EventsV1Event(
            metadata=client.V1ObjectMeta(
                generate_name=f"{name}-",
                namespace=namespace
            ),
            reason=reason,
            note=message,
            type=event_type,
            reporting_controller=EVENT_COMPONENT,
            reporting_instance=connection.hostname,
            action="Scaling",
            regarding=client.V1ObjectReference(
                api_version=api_version,
                kind=kind,
                name=name,
                namespace=namespace,
                uid=uid
            ),
            event_time=now
        )

        # Create the event in the Kubernetes API
        connection.events_v1_api.create_namespaced_event(
            namespace=namespace,
            body=body
        )
        logger.debug(f"Created event for {kind} {namespace}/{name}: {reason}")

    except Exception as e:
        logger.warning(
            f"Failed to create event for {kind} {namespace}/{name}: {e}")
