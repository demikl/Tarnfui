"""Kubernetes client module for Tarnfui.

This module handles all interactions with the Kubernetes API.
"""
import logging

from kubernetes import client, config

logger = logging.getLogger(__name__)

# Key used for storing replica count in deployment annotations
TARNFUI_REPLICAS_ANNOTATION = "tarnfui.io/original-replicas"


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
        # Dictionary to store the original replica counts for deployments that have no annotations
        # Used as a fallback for deployments that don't support annotations or in case of errors
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

        Stores the replica count in both an annotation on the deployment
        and in the memory cache as a fallback.

        Args:
            deployment: The deployment object to save the state for.
        """
        name = deployment.metadata.name
        namespace = deployment.metadata.namespace
        replicas = deployment.spec.replicas

        if replicas <= 0:
            logger.debug(
                f"Skipping save for deployment {namespace}/{name} with 0 replicas")
            return

        key = f"{namespace}/{name}"

        # Save in memory as a fallback
        self.deployment_replicas[key] = replicas

        try:
            # Save as an annotation on the deployment
            if deployment.metadata.annotations is None:
                deployment.metadata.annotations = {}

            deployment.metadata.annotations[TARNFUI_REPLICAS_ANNOTATION] = str(
                replicas)

            # Update the deployment with the new annotation
            self.api.patch_namespaced_deployment(
                name=name,
                namespace=namespace,
                body={"metadata": {"annotations": {
                    TARNFUI_REPLICAS_ANNOTATION: str(replicas)}}}
            )
            logger.info(
                f"Saved state for deployment {key} in annotation: {replicas} replicas")
        except Exception as e:
            logger.warning(
                f"Failed to save state in annotation for deployment {key}: {e}")
            logger.info(f"State saved in memory only: {replicas} replicas")

    def get_original_replicas(self, deployment: client.V1Deployment) -> int | None:
        """Get the original replica count for a deployment.

        Tries to retrieve from annotations first, falls back to in-memory cache.

        Args:
            deployment: The deployment to get the original replica count for.

        Returns:
            The original replica count, or None if not found.
        """
        name = deployment.metadata.name
        namespace = deployment.metadata.namespace
        key = f"{namespace}/{name}"

        # Try to get from annotations first
        if (deployment.metadata.annotations and
                TARNFUI_REPLICAS_ANNOTATION in deployment.metadata.annotations):
            try:
                replicas = int(
                    deployment.metadata.annotations[TARNFUI_REPLICAS_ANNOTATION])
                logger.info(
                    f"Retrieved original replicas from annotation for {key}: {replicas}")
                return replicas
            except (ValueError, TypeError) as e:
                logger.warning(
                    f"Invalid replica count in annotation for {key}: {e}")

        # Fall back to in-memory cache
        if key in self.deployment_replicas:
            replicas = self.deployment_replicas[key]
            logger.info(
                f"Retrieved original replicas from memory cache for {key}: {replicas}")
            return replicas

        logger.warning(f"No saved state found for deployment {key}")
        return None

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
        if replicas == 0 and deployment.spec.replicas > 0:
            self.save_deployment_state(deployment)

        # Apply the new scale
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
            # Only restore deployments that are currently scaled to 0
            if deployment.spec.replicas > 0:
                continue

            original_replicas = self.get_original_replicas(deployment)

            if original_replicas is not None and original_replicas > 0:
                self.scale_deployment(deployment, original_replicas)
                logger.info(
                    f"Restored deployment {deployment.metadata.namespace}/{deployment.metadata.name} to {original_replicas} replicas")
            else:
                # Default to 1 replica if no saved state is found
                logger.warning(
                    f"No original replica count found for {deployment.metadata.namespace}/{deployment.metadata.name}, defaulting to 1")
                self.scale_deployment(deployment, 1)
