"""Kubernetes StatefulSets handling module.

This module provides specific functionality for managing Kubernetes StatefulSets.
"""

import logging

from kubernetes import client

from tarnfui.kubernetes.connection import KubernetesConnection
from tarnfui.kubernetes.resources.workloads import ReplicatedWorkloadResource

logger = logging.getLogger(__name__)


class StatefulSetResource(ReplicatedWorkloadResource[client.V1StatefulSet]):
    """Handler for Kubernetes StatefulSet resources."""

    # Resource type specific constants
    RESOURCE_API_VERSION = "apps/v1"
    RESOURCE_KIND = "StatefulSet"

    def __init__(self, connection: KubernetesConnection, namespace: str | None = None):
        """Initialize the StatefulSet resource handler.

        Args:
            connection: The Kubernetes connection to use
            namespace: Optional namespace to filter resources. If None, all namespaces will be used.
        """
        super().__init__(connection, namespace)
        # API client for statefulsets
        self.api = connection.apps_v1_api

    def get_resource(self, name: str, namespace: str) -> client.V1StatefulSet:
        """Get a specific statefulset by name.

        Args:
            name: Name of the statefulset.
            namespace: Namespace of the statefulset.

        Returns:
            The statefulset object.
        """
        return self.api.read_namespaced_stateful_set(name, namespace)

    def patch_resource(self, resource: client.V1StatefulSet, body: dict) -> None:
        """Patch a statefulset with the given body.

        Args:
            resource: The statefulset to patch.
            body: The patch body to apply.
        """
        self.api.patch_namespaced_stateful_set(
            name=resource.metadata.name,
            namespace=resource.metadata.namespace,
            body=body,
        )

    def list_namespaced_resources(self, namespace: str, **kwargs) -> any:
        """List statefulsets in a specific namespace.

        Args:
            namespace: The namespace to list statefulsets in.
            **kwargs: Additional arguments to pass to the API call.

        Returns:
            The API response containing the list of statefulsets.
        """
        return self.api.list_namespaced_stateful_set(namespace, **kwargs)

    def list_all_namespaces_resources(self, **kwargs) -> any:
        """List statefulsets across all namespaces.

        Args:
            **kwargs: Additional arguments to pass to the API call.

        Returns:
            The API response containing the list of statefulsets.
        """
        return self.api.list_stateful_set_for_all_namespaces(**kwargs)
