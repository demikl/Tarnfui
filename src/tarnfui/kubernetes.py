"""Kubernetes client module for Tarnfui.

This module handles all interactions with the Kubernetes API.
"""
import logging

from kubernetes import client, config

logger = logging.getLogger(__name__)


class KubernetesClient:
    """Client for interacting with the Kubernetes API.

    This class handles all operations related to managing deployments in the Kubernetes cluster.
    """

    def __init__(self, namespace: str | None = None):
        """Initialize the Kubernetes client.

        Args:
            namespace: Optional namespace to filter resources. If None, all namespaces will be used.
        """
        try:
            # Try to load in-cluster config first (for when running in a pod)
            config.load_incluster_config()
            logger.info("Using in-cluster configuration")
        except config.ConfigException:
            # Fall back to kubeconfig for local development
            config.load_kube_config()
            logger.info("Using kubeconfig configuration")

        self.api = client.AppsV1Api()
        self.namespace = namespace
        # Dictionary to store the original replica counts for deployments
        self.deployment_replicas: dict[str, int] = {}

    def list_deployments(self, namespace: str | None = None) -> list[client.V1Deployment]:
        """List all deployments in the specified namespace or all namespaces.

        Args:
            namespace: Namespace to list deployments from. If None, use the client's namespace.

        Returns:
            List of deployment objects.
        """
        ns = namespace or self.namespace

        if ns:
            logger.info(f"Listing deployments in namespace {ns}")
            return self.api.list_namespaced_deployment(ns).items
        else:
            logger.info("Listing deployments across all namespaces")
            return self.api.list_deployment_for_all_namespaces().items

    def save_deployment_state(self, deployment: client.V1Deployment) -> None:
        """Save the current replica count for a deployment.

        Args:
            deployment: The deployment object to save the state for.
        """
        name = deployment.metadata.name
        namespace = deployment.metadata.namespace
        replicas = deployment.spec.replicas

        key = f"{namespace}/{name}"
        if replicas > 0:  # Only save if there are active replicas
            self.deployment_replicas[key] = replicas
            logger.info(
                f"Saved state for deployment {key}: {replicas} replicas")

    def scale_deployment(self, deployment: client.V1Deployment, replicas: int) -> None:
        """Scale a deployment to the specified number of replicas.

        Args:
            deployment: The deployment object to scale.
            replicas: The number of replicas to scale to.
        """
        name = deployment.metadata.name
        namespace = deployment.metadata.namespace

        logger.info(
            f"Scaling deployment {namespace}/{name} to {replicas} replicas")

        # Save the current state if scaling to zero
        if replicas == 0:
            self.save_deployment_state(deployment)

        # Apply the new scale
        deployment.spec.replicas = replicas
        self.api.patch_namespaced_deployment(
            name=name,
            namespace=namespace,
            body={"spec": {"replicas": replicas}}
        )

    def stop_deployments(self, namespace: str | None = None) -> None:
        """Scale all deployments to zero replicas.

        Args:
            namespace: Namespace to stop deployments in. If None, use the client's namespace.
        """
        deployments = self.list_deployments(namespace)

        for deployment in deployments:
            # Skip deployments that are already scaled to 0
            if deployment.spec.replicas == 0:
                continue

            self.scale_deployment(deployment, 0)

    def start_deployments(self, namespace: str | None = None) -> None:
        """Restore all deployments to their original replica counts.

        Args:
            namespace: Namespace to start deployments in. If None, use the client's namespace.
        """
        deployments = self.list_deployments(namespace)

        for deployment in deployments:
            name = deployment.metadata.name
            ns = deployment.metadata.namespace
            key = f"{ns}/{name}"

            if key in self.deployment_replicas:
                original_replicas = self.deployment_replicas[key]
                # Only scale up if current replicas is 0
                if deployment.spec.replicas == 0:
                    self.scale_deployment(deployment, original_replicas)
                    logger.info(
                        f"Restored deployment {key} to {original_replicas} replicas")
            else:
                logger.warning(
                    f"No saved state for deployment {key}, cannot restore")
