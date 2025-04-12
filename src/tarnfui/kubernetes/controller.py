"""Kubernetes controller module.

This module provides a controller for managing Kubernetes resources.
"""
import logging

from tarnfui.kubernetes.base import KubernetesResource
from tarnfui.kubernetes.connection import KubernetesConnection
from tarnfui.kubernetes.resources.deployments import DeploymentResource

logger = logging.getLogger(__name__)


class KubernetesController:
    """Controller for managing Kubernetes resources.

    This class provides a central controller for managing all types of Kubernetes resources.
    It delegates operations to specialized resource handlers based on the resource type.
    """

    def __init__(self, namespace: str | None = None):
        """Initialize the Kubernetes controller.

        Args:
            namespace: Optional namespace to filter resources. If None, all namespaces will be used.
        """
        self.namespace = namespace
        self.connection = KubernetesConnection()

        # Initialize resource handlers
        self.resources: dict[str, KubernetesResource] = {}
        self._register_resources()

    def _register_resources(self) -> None:
        """Register all supported resource types with their handlers."""
        # Register standard resource types
        self.register_resource("deployments", DeploymentResource(
            self.connection, self.namespace))

        # In the future, register additional resource types here:
        # self.register_resource("statefulsets", StatefulSetResource(self.connection, self.namespace))
        # self.register_resource("daemonsets", DaemonSetResource(self.connection, self.namespace))

    def register_resource(self, resource_type: str, handler: KubernetesResource) -> None:
        """Register a resource handler.

        Args:
            resource_type: The name of the resource type.
            handler: The handler instance for this resource type.
        """
        self.resources[resource_type] = handler
        logger.debug(f"Registered resource handler for {resource_type}")

    def get_handler(self, resource_type: str) -> KubernetesResource | None:
        """Get the handler for a specific resource type.

        Args:
            resource_type: The name of the resource type.

        Returns:
            The handler for the requested resource type, or None if not found.
        """
        handler = self.resources.get(resource_type)
        if not handler:
            logger.warning(
                f"No handler registered for resource type {resource_type}")
        return handler

    def stop_resources(self, resource_types: list[str] | None = None, namespace: str | None = None) -> None:
        """Scale resources to zero replicas.

        Args:
            resource_types: List of resource types to stop. If None, all registered types are used.
            namespace: Namespace to stop resources in. If None, use the controller's namespace.
        """
        ns = namespace or self.namespace
        types_to_stop = resource_types or list(self.resources.keys())

        for resource_type in types_to_stop:
            handler = self.get_handler(resource_type)
            if handler:
                logger.info(f"Stopping {resource_type}")
                handler.stop_resources(namespace=ns)

    def start_resources(self, resource_types: list[str] | None = None, namespace: str | None = None) -> None:
        """Restore resources to their original replica counts.

        Args:
            resource_types: List of resource types to start. If None, all registered types are used.
            namespace: Namespace to start resources in. If None, use the controller's namespace.
        """
        ns = namespace or self.namespace
        types_to_start = resource_types or list(self.resources.keys())

        for resource_type in types_to_start:
            handler = self.get_handler(resource_type)
            if handler:
                logger.info(f"Starting {resource_type}")
                handler.start_resources(namespace=ns)
