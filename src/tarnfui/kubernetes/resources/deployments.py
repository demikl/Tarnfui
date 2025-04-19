"""Kubernetes Deployments handling module.

This module provides specific functionality for managing Kubernetes Deployments.
"""

import logging

from kubernetes import client

from tarnfui.kubernetes.connection import KubernetesConnection
from tarnfui.kubernetes.resources.workloads import ReplicatedWorkloadResource

logger = logging.getLogger(__name__)


class DeploymentResource(ReplicatedWorkloadResource[client.V1Deployment]):
    """Handler for Kubernetes Deployment resources."""

    # Resource type specific constants
    RESOURCE_API_VERSION = "apps/v1"
    RESOURCE_KIND = "Deployment"

    def __init__(self, connection: KubernetesConnection, namespace: str | None = None):
        """Initialize the Deployment resource handler.

        Args:
            connection: The Kubernetes connection to use
            namespace: Optional namespace to filter resources. If None, all namespaces will be used.
        """
        super().__init__(connection, namespace)
        # API client for deployments
        self.api = connection.apps_v1_api

    def get_resource(self, name: str, namespace: str) -> client.V1Deployment:
        """Get a specific deployment by name.

        Args:
            name: Name of the deployment.
            namespace: Namespace of the deployment.

        Returns:
            The deployment object.
        """
        return self.api.read_namespaced_deployment(name, namespace)

    def patch_resource(self, resource: client.V1Deployment, body: dict) -> None:
        """Patch a deployment with the given body.

        Args:
            resource: The deployment to patch.
            body: The patch body to apply.
        """
        self.api.patch_namespaced_deployment(
            name=resource.metadata.name,
            namespace=resource.metadata.namespace,
            body=body,
        )

    def list_namespaced_resources(self, namespace: str, **kwargs) -> any:
        """List deployments in a specific namespace.

        Args:
            namespace: The namespace to list deployments in.
            **kwargs: Additional arguments to pass to the API call.

        Returns:
            The API response containing the list of deployments.
        """
        return self.api.list_namespaced_deployment(namespace, **kwargs)

    def list_all_namespaces_resources(self, **kwargs) -> any:
        """List deployments across all namespaces.

        Args:
            **kwargs: Additional arguments to pass to the API call.

        Returns:
            The API response containing the list of deployments.
        """
        return self.api.list_deployment_for_all_namespaces(**kwargs)
