"""Kubernetes Deployments handling module.

This module provides specific functionality for managing Kubernetes Deployments.
"""

import logging

from kubernetes import client
from kubernetes.client.rest import ApiException

from tarnfui.kubernetes.base import KubernetesResource
from tarnfui.kubernetes.connection import KubernetesConnection

logger = logging.getLogger(__name__)


class DeploymentResource(KubernetesResource[client.V1Deployment]):
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

    def iter_resources(self, namespace: str | None = None, batch_size: int = 100) -> list[client.V1Deployment]:
        """Iterate over all deployments in a namespace or across all namespaces.

        Uses pagination to fetch deployments in batches and yield them one by one
        to limit memory usage.

        Args:
            namespace: Namespace to get deployments from. If None, use the handler's namespace.
            batch_size: Number of deployments to fetch per API call.

        Yields:
            Deployments, one at a time.
        """
        ns = namespace or self.namespace
        continue_token = None

        try:
            while True:
                # Fetch current page of deployments
                if ns:
                    result = self.api.list_namespaced_deployment(
                        ns, limit=batch_size, _continue=continue_token)
                else:
                    result = self.api.list_deployment_for_all_namespaces(
                        limit=batch_size, _continue=continue_token)

                # Yield deployments from this page one by one
                yield from result.items

                # Check if there are more pages to process
                continue_token = result.metadata._continue
                if not continue_token:
                    break

        except ApiException as e:
            logger.error(f"Error getting deployments: {e}")
            return

    def get_resource(self, name: str, namespace: str) -> client.V1Deployment:
        """Get a specific deployment by name.

        Args:
            name: Name of the deployment.
            namespace: Namespace of the deployment.

        Returns:
            The deployment object.
        """
        return self.api.read_namespaced_deployment(name, namespace)

    def get_replicas(self, deployment: client.V1Deployment) -> int:
        """Get the current replica count for a deployment.

        Args:
            deployment: The deployment to get the replica count from.

        Returns:
            The current replica count.
        """
        return deployment.spec.replicas or 0

    def get_current_state(self, deployment: client.V1Deployment) -> int:
        """Get the current state of a deployment.

        For Deployments, the state is represented by the replica count.

        Args:
            deployment: The deployment to get the state from.

        Returns:
            The current replica count.
        """
        return self.get_replicas(deployment)

    def suspend_resource(self, deployment: client.V1Deployment) -> None:
        """Suspend a deployment by setting replicas to 0.

        Args:
            deployment: The deployment to suspend.
        """
        self.set_replicas(deployment, 0)

    def resume_resource(self, deployment: client.V1Deployment, saved_state: int) -> None:
        """Resume a deployment by restoring its replica count.

        Args:
            deployment: The deployment to resume.
            saved_state: The saved replica count to restore.
        """
        self.set_replicas(deployment, saved_state)

    def is_suspended(self, deployment: client.V1Deployment) -> bool:
        """Check if a deployment is currently suspended.

        A deployment is considered suspended if it has 0 replicas.

        Args:
            deployment: The deployment to check.

        Returns:
            True if the deployment is suspended (has 0 replicas), False otherwise.
        """
        return self.get_replicas(deployment) == 0

    def set_replicas(self, deployment: client.V1Deployment, replicas: int) -> None:
        """Set the replica count for a deployment.

        Args:
            deployment: The deployment to set the replica count for.
            replicas: The number of replicas to set.
        """
        try:
            self.api.patch_namespaced_deployment(
                name=deployment.metadata.name,
                namespace=deployment.metadata.namespace,
                body={"spec": {"replicas": replicas}},
            )
        except ApiException as e:
            logger.error(
                f"Error setting replicas for deployment {deployment.metadata.namespace}/{deployment.metadata.name}: {e}"
            )
            raise

    def get_resource_key(self, deployment: client.V1Deployment) -> str:
        """Get a unique key for a deployment.

        Args:
            deployment: The deployment to get the key for.

        Returns:
            A string that uniquely identifies the deployment.
        """
        return f"{deployment.metadata.namespace}/{deployment.metadata.name}"

    def get_resource_name(self, deployment: client.V1Deployment) -> str:
        """Get the name of a deployment.

        Args:
            deployment: The deployment to get the name for.

        Returns:
            The name of the deployment.
        """
        return deployment.metadata.name

    def get_resource_namespace(self, deployment: client.V1Deployment) -> str:
        """Get the namespace of a deployment.

        Args:
            deployment: The deployment to get the namespace for.

        Returns:
            The namespace of the deployment.
        """
        return deployment.metadata.namespace

    def _save_annotation(self, deployment: client.V1Deployment, annotation_key: str, annotation_value: str) -> None:
        """Save an annotation on a deployment.

        Args:
            deployment: The deployment to annotate.
            annotation_key: The annotation key.
            annotation_value: The annotation value.
        """
        try:
            self.api.patch_namespaced_deployment(
                name=deployment.metadata.name,
                namespace=deployment.metadata.namespace,
                body={"metadata": {"annotations": {
                    annotation_key: annotation_value}}},
            )
        except ApiException as e:
            logger.error(
                f"Error saving annotation for deployment "
                f"{deployment.metadata.namespace}/{deployment.metadata.name}: {e}"
            )
            raise

    def _get_annotation(self, deployment: client.V1Deployment, annotation_key: str) -> str | None:
        """Get an annotation from a deployment.

        Args:
            deployment: The deployment to get the annotation from.
            annotation_key: The annotation key to get.

        Returns:
            The annotation value, or None if not found.
        """
        if (
            hasattr(deployment.metadata, "annotations")
            and deployment.metadata.annotations
            and annotation_key in deployment.metadata.annotations
        ):
            return deployment.metadata.annotations[annotation_key]
        return None
