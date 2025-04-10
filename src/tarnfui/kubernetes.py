"""Kubernetes client module for Tarnfui.

This module handles all interactions with the Kubernetes API.
"""
import logging
import os
import socket
from datetime import UTC, datetime

from kubernetes import client, config

logger = logging.getLogger(__name__)

# Key used for storing replica count in deployment annotations
TARNFUI_REPLICAS_ANNOTATION = "tarnfui.io/original-replicas"
# Constants for event types
EVENT_TYPE_NORMAL = "Normal"
EVENT_TYPE_WARNING = "Warning"
# Constants for event reasons
EVENT_REASON_STOPPED = "Stopped"
EVENT_REASON_STARTED = "Started"
# Component name for events
EVENT_COMPONENT = "tarnfui"


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
            try:
                # Fall back to kubeconfig for local development
                config.load_kube_config()
                logger.info("Using kubeconfig configuration")
            except config.ConfigException as e:
                # Provide a clear error message if kubeconfig is not available or invalid
                logger.error(
                    "Failed to load Kubernetes configuration. Ensure that the kubeconfig file is available and valid."
                )
                raise RuntimeError(
                    "Kubernetes configuration error: kubeconfig file is missing or invalid.") from e

        self.api = client.AppsV1Api()
        self.events_api = client.EventsV1Api()
        self.namespace = namespace
        # Dictionary to store the original replica counts for deployments that have no annotations
        # Used as a fallback for deployments that don't support annotations or in case of errors
        self.deployment_replicas: dict[str, int] = {}
        # Get hostname for event reporting
        self.hostname = socket.gethostname()
        # Unique identifier for this instance
        self.instance_id = os.environ.get("HOSTNAME", self.hostname)

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

    def create_event(
        self,
        deployment: client.V1Deployment,
        event_type: str,
        reason: str,
        message: str
    ) -> None:
        """Create a Kubernetes event for the given deployment.

        Args:
            deployment: The deployment to create an event for.
            event_type: Type of event (Normal or Warning)
            reason: Short reason for the event
            message: Detailed message for the event
        """
        try:
            # Use datetime with timezone info instead of utcnow
            now = datetime.now(UTC)

            # Initialize the event body
            body = client.EventsV1Event(
                metadata=client.V1ObjectMeta(
                    generate_name=f"{deployment.metadata.name}-",
                    namespace=deployment.metadata.namespace
                ),
                reason=reason,
                note=message,
                type=event_type,
                reporting_controller=EVENT_COMPONENT,
                reporting_instance=self.hostname,
                action="Scaling",
                regarding=client.V1ObjectReference(
                    api_version="apps/v1",
                    kind="Deployment",
                    name=deployment.metadata.name,
                    namespace=deployment.metadata.namespace,
                    uid=deployment.metadata.uid
                ),
                event_time=now
            )

            # Create the event in the Kubernetes API
            self.events_api.create_namespaced_event(
                namespace=deployment.metadata.namespace,
                body=body
            )
            logger.info(
                f"Created event for deployment {deployment.metadata.namespace}/{deployment.metadata.name}: {reason}")

        except Exception as e:
            logger.warning(
                f"Failed to create event for deployment {deployment.metadata.namespace}/"
                f"{deployment.metadata.name}: {e}"
            )

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

        current_replicas = deployment.spec.replicas

        # Save the current state if scaling to zero
        if replicas == 0 and current_replicas > 0:
            self.save_deployment_state(deployment)

            # Create a "Stopped" event
            event_message = f"Scaled down deployment from {current_replicas} to 0 replicas by Tarnfui"
            self.create_event(
                deployment=deployment,
                event_type=EVENT_TYPE_NORMAL,
                reason=EVENT_REASON_STOPPED,
                message=event_message
            )

        # Create a "Started" event when scaling up
        elif replicas > 0 and current_replicas == 0:
            event_message = f"Scaled up deployment from 0 to {replicas} replicas by Tarnfui"
            self.create_event(
                deployment=deployment,
                event_type=EVENT_TYPE_NORMAL,
                reason=EVENT_REASON_STARTED,
                message=event_message
            )

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

        logger.info(
            f"Completed processing {len(deployments)} deployments.")

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
                    f"Restored deployment {deployment.metadata.namespace}/"
                    f"{deployment.metadata.name} to {original_replicas} replicas"
                )
            else:
                # Default to scaling to 1 replica if no saved state is found
                self.scale_deployment(deployment, 1)
                logger.info(
                    f"Defaulted deployment {deployment.metadata.namespace}/{deployment.metadata.name} to 1 replica")

        logger.info(
            f"Completed processing {len(deployments)} deployments.")
