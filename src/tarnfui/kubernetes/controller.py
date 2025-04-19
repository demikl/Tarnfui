"""Kubernetes controller module.

This module provides a controller for managing Kubernetes resources.
"""

import logging
from typing import Any

from tarnfui.kubernetes.base import KubernetesResource
from tarnfui.kubernetes.connection import KubernetesConnection
from tarnfui.kubernetes.resources.deployments import DeploymentResource
from tarnfui.kubernetes.resources.statefulsets import StatefulSetResource

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
        self.register_resource("deployments", DeploymentResource(self.connection, self.namespace))
        self.register_resource("statefulsets", StatefulSetResource(self.connection, self.namespace))

        # In the future, register additional resource types here:
        # self.register_resource("daemonsets", DaemonSetResource(self.connection, self.namespace))
        # self.register_resource("kustomizations", KustomizationResource(self.connection, self.namespace))

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
            logger.warning(f"No handler registered for resource type {resource_type}")
        return handler

    def suspend_resources(self, resource_types: list[str] | None = None, namespace: str | None = None) -> None:
        """Suspend resources.

        This method suspends resources by calling the resource-specific suspend_resource method.
        For deployments and statefulsets, this means scaling to zero replicas.
        For other resources, it may mean setting a different property, like spec.suspend for Kustomizations.

        Args:
            resource_types: List of resource types to suspend. If None, all registered types are used.
            namespace: Namespace to suspend resources in. If None, use the controller's namespace.
        """
        ns = namespace or self.namespace
        types_to_suspend = resource_types or list(self.resources.keys())

        for resource_type in types_to_suspend:
            handler = self.get_handler(resource_type)
            if handler:
                logger.info(f"Suspending {resource_type}")
                handler.stop_resources(namespace=ns)

    def resume_resources(self, resource_types: list[str] | None = None, namespace: str | None = None) -> None:
        """Resume resources.

        This method resumes resources by calling the resource-specific resume_resource method.
        For deployments and statefulsets, this means restoring the original replica count.
        For other resources, it may mean setting a different property, like spec.suspend for Kustomizations.

        Args:
            resource_types: List of resource types to resume. If None, all registered types are used.
            namespace: Namespace to resume resources in. If None, use the controller's namespace.
        """
        ns = namespace or self.namespace
        types_to_resume = resource_types or list(self.resources.keys())

        for resource_type in types_to_resume:
            handler = self.get_handler(resource_type)
            if handler:
                logger.info(f"Resuming {resource_type}")
                handler.start_resources(namespace=ns)

    def get_resource_state(self, resource_type: str, name: str, namespace: str) -> Any | None:
        """Get the current state of a specific resource.

        Args:
            resource_type: The type of the resource.
            name: The name of the resource.
            namespace: The namespace of the resource.

        Returns:
            The current state of the resource, or None if not found.
        """
        handler = self.get_handler(resource_type)
        if not handler:
            return None

        try:
            resource = handler.get_resource(name, namespace)
            return handler.get_current_state(resource)
        except Exception as e:
            logger.error(f"Error getting state for {resource_type} {namespace}/{name}: {e}")
            return None

    def get_saved_state(self, resource_type: str, name: str, namespace: str) -> Any | None:
        """Get the saved state of a specific resource.

        Args:
            resource_type: The type of the resource.
            name: The name of the resource.
            namespace: The namespace of the resource.

        Returns:
            The saved state of the resource, or None if not found.
        """
        handler = self.get_handler(resource_type)
        if not handler:
            return None

        try:
            resource = handler.get_resource(name, namespace)
            return handler.get_saved_state(resource)
        except Exception as e:
            logger.error(f"Error getting saved state for {resource_type} {namespace}/{name}: {e}")
            return None
