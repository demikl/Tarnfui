"""Kubernetes client module for Tarnfui.

This module handles all interactions with the Kubernetes API.
"""

import logging

from tarnfui.kubernetes.controller import KubernetesController

logger = logging.getLogger(__name__)

# Constants for event types (for backward compatibility)
EVENT_TYPE_NORMAL = "Normal"
EVENT_TYPE_WARNING = "Warning"
# Constants for event reasons (for backward compatibility)
EVENT_REASON_STOPPED = "Stopped"
EVENT_REASON_STARTED = "Started"
# Component name for events (for backward compatibility)
EVENT_COMPONENT = "tarnfui"
# Key used for storing replica count in deployment annotations (for backward compatibility)
TARNFUI_REPLICAS_ANNOTATION = "tarnfui.io/original-replicas"


class KubernetesClient:
    """Client for interacting with the Kubernetes API.

    This class is maintained for backward compatibility. It forwards operations
    to the new KubernetesController implementation.

    For new code, use the KubernetesController class directly.
    """

    def __init__(self, namespace=None):
        """Initialize the Kubernetes client.

        Args:
            namespace: Optional namespace to filter resources. If None, all namespaces will be used.
        """
        self.controller = KubernetesController(namespace=namespace)
        self.namespace = namespace

        # For backward compatibility, expose some of the controller's attributes
        connection = self.controller.connection
        self.api = connection.apps_v1_api
        self.core_api = connection.core_v1_api
        self.events_api = connection.events_v1_api
        self.hostname = connection.hostname
        self.instance_id = connection.instance_id
        self.api_client = connection.api_client
        self.host = connection.host
        self.auth_headers = connection.auth_headers
        self.cert_file = connection.cert_file
        self.key_file = connection.key_file
        self.verify_ssl = connection.verify_ssl
        self.ssl_ca_cert = connection.ssl_ca_cert

        # This dictionary is used by the original implementation for deployment state
        deployment_handler = self.controller.get_handler("deployments")
        self.deployment_replicas = deployment_handler._memory_state if deployment_handler else {}

    def create_event(self, deployment, event_type, reason, message):
        """Create a Kubernetes event for the given deployment.

        Args:
            deployment: The deployment to create an event for.
            event_type: Type of event (Normal or Warning)
            reason: Short reason for the event
            message: Detailed message for the event
        """
        from tarnfui.kubernetes.resources.events import create_scaling_event

        create_scaling_event(
            connection=self.controller.connection,
            resource=deployment,
            api_version="apps/v1",
            kind="Deployment",
            event_type=event_type,
            reason=reason,
            message=message,
        )

    def save_deployment_state(self, deployment):
        """Save the current replica count for a deployment.

        Args:
            deployment: The deployment object to save the state for.
        """
        handler = self.controller.get_handler("deployments")
        if handler:
            # Convert dictionary format if needed
            if isinstance(deployment, dict):
                from kubernetes import client

                name = deployment["metadata"]["name"]
                namespace = deployment["metadata"]["namespace"]
                try:
                    # Try to get the full deployment
                    deployment = handler.get_resource(name, namespace)
                except Exception:
                    # Fall back to creating a minimal deployment object
                    deployment = client.V1Deployment(
                        metadata=client.V1ObjectMeta(name=name, namespace=namespace),
                        spec=client.V1DeploymentSpec(replicas=deployment["spec"]["replicas"]),
                    )

            handler.save_resource_state(deployment)

    def get_original_replicas(self, deployment):
        """Get the original replica count for a deployment.

        Args:
            deployment: The deployment to get the original replica count for.

        Returns:
            The original replica count, or None if not found.
        """
        handler = self.controller.get_handler("deployments")
        if handler:
            # Convert dictionary format if needed
            if isinstance(deployment, dict):
                from kubernetes import client

                name = deployment["metadata"]["name"]
                namespace = deployment["metadata"]["namespace"]
                try:
                    # Try to get the full deployment
                    deployment = handler.get_resource(name, namespace)
                except Exception:
                    # Fall back to creating a minimal deployment object
                    deployment = client.V1Deployment(
                        metadata=client.V1ObjectMeta(name=name, namespace=namespace),
                        spec=client.V1DeploymentSpec(replicas=deployment["spec"].get("replicas", 0)),
                    )

            return handler.get_original_replicas(deployment)
        return None

    def scale_deployment(self, deployment, replicas):
        """Scale a deployment to the specified number of replicas.

        Args:
            deployment: The deployment object to scale.
            replicas: The number of replicas to scale to.
        """
        handler = self.controller.get_handler("deployments")
        if handler:
            # Convert dictionary format if needed
            if isinstance(deployment, dict):
                from kubernetes import client

                name = deployment["metadata"]["name"]
                namespace = deployment["metadata"]["namespace"]
                try:
                    # Try to get the full deployment
                    deployment = handler.get_resource(name, namespace)
                except Exception:
                    # Fall back to creating a minimal deployment object
                    deployment = client.V1Deployment(
                        metadata=client.V1ObjectMeta(name=name, namespace=namespace),
                        spec=client.V1DeploymentSpec(replicas=deployment["spec"].get("replicas", 0)),
                    )

            handler.scale(deployment, replicas)

    def stop_deployments(self, namespace=None, batch_size=100):
        """Scale all deployments to zero replicas.

        Args:
            namespace: Namespace to stop deployments in. If None, use the client's namespace.
            batch_size: Number of deployments to process per batch.
        """
        self.controller.stop_resources(["deployments"], namespace=namespace)

    def start_deployments(self, namespace=None, batch_size=100):
        """Restore all deployments to their original replica counts.

        Args:
            namespace: Namespace to start deployments in. If None, use the client's namespace.
            batch_size: Number of deployments to process per batch.
        """
        self.controller.start_resources(["deployments"], namespace=namespace)

    def _get_deployment_light(self, name, namespace):
        """Get a specific deployment by name with minimal data.

        Args:
            name: Name of the deployment.
            namespace: Namespace of the deployment.

        Returns:
            The deployment object with minimal data.
        """
        handler = self.controller.get_handler("deployments")
        if handler:
            return handler.get_resource(name, namespace)
        return self.api.read_namespaced_deployment(name, namespace)

    def _ensure_full_deployment_object(self, deployment):
        """Ensure we have a full deployment object for operations that need it.

        Args:
            deployment: Either a minimal deployment dict or full V1Deployment object

        Returns:
            A full V1Deployment object
        """
        # If it's already a V1Deployment, return it
        from kubernetes import client

        if isinstance(deployment, client.V1Deployment):
            return deployment

        # If it's our minimal object, fetch the full deployment
        if isinstance(deployment, dict):
            name = deployment["metadata"]["name"]
            namespace = deployment["metadata"]["namespace"]
            return self._get_deployment_light(name, namespace)

        # Otherwise convert the dict to a V1Deployment object
        return client.V1Deployment(
            metadata=client.V1ObjectMeta(
                name=deployment["metadata"]["name"], namespace=deployment["metadata"]["namespace"]
            ),
            spec=client.V1DeploymentSpec(replicas=deployment["spec"]["replicas"]),
        )
