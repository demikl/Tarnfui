"""Kubernetes client module for Tarnfui.

This module handles all interactions with the Kubernetes API.
"""
import json
import logging
import os
import socket
from datetime import UTC, datetime
from typing import Any

import requests
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
        self.core_api = client.CoreV1Api()
        self.events_api = client.EventsV1Api()
        self.namespace = namespace
        # Dictionary to store the original replica counts for deployments that have no annotations
        # Used as a fallback for deployments that don't support annotations or in case of errors
        self.deployment_replicas: dict[str, int] = {}
        # Get hostname for event reporting
        self.hostname = socket.gethostname()
        # Unique identifier for this instance
        self.instance_id = os.environ.get("HOSTNAME", self.hostname)

        # Setup for direct API access
        self.api_client = self.api.api_client
        self.host = self.api_client.configuration.host

        # Get authentication credentials from the configuration
        self.auth_headers = {}

        # Handle token-based authentication
        if hasattr(self.api_client.configuration, 'api_key'):
            # Add Bearer token if available
            auth_settings = self.api_client.configuration.auth_settings()
            for auth in auth_settings.values():
                if auth['in'] == 'header' and auth.get('value'):
                    self.auth_headers[auth['key']] = auth['value']

        # Handle certificate-based authentication
        self.cert_file = None
        self.key_file = None
        if hasattr(self.api_client.configuration, 'cert_file') and self.api_client.configuration.cert_file:
            self.cert_file = self.api_client.configuration.cert_file
        if hasattr(self.api_client.configuration, 'key_file') and self.api_client.configuration.key_file:
            self.key_file = self.api_client.configuration.key_file

        # Setup SSL verification
        self.verify_ssl = self.api_client.configuration.verify_ssl
        self.ssl_ca_cert = self.api_client.configuration.ssl_ca_cert

    def _get_deployment_light(self, name: str, namespace: str) -> client.V1Deployment:
        """Get a specific deployment by name with minimal data.

        Args:
            name: Name of the deployment.
            namespace: Namespace of the deployment.

        Returns:
            The deployment object with minimal data.
        """
        return self.api.read_namespaced_deployment(name, namespace)

    def list_deployments(self, namespace: str | None = None) -> list[dict[str, Any]]:
        """List all deployments in the specified namespace or all namespaces with minimal data.

        Args:
            namespace: Namespace to list deployments from. If None, use the client's namespace.

        Returns:
            List of deployment objects with minimal data.
        """
        ns = namespace or self.namespace

        try:
            # Prepare the URL for API request
            if ns:
                logger.info(f"Listing deployments in namespace {ns}")
                url = f"{self.host}/apis/apps/v1/namespaces/{ns}/deployments"
            else:
                logger.info("Listing deployments across all namespaces")
                url = f"{self.host}/apis/apps/v1/deployments"

            # Add headers for table format to reduce data transferred
            headers = {
                "Accept": "application/json;as=Table;g=meta.k8s.io;v=v1",
                **self.auth_headers
            }

            # Setup request kwargs with proper authentication
            request_kwargs = {
                "headers": headers,
                "verify": self.ssl_ca_cert if self.verify_ssl else False
            }

            # Add certificate-based authentication if available
            if self.cert_file and self.key_file:
                request_kwargs["cert"] = (self.cert_file, self.key_file)
                logger.debug("Using client certificate authentication")
            elif self.auth_headers:
                logger.debug("Using token-based authentication")
            else:
                logger.debug(
                    "No explicit authentication method found, relying on default configuration")

            # Make the API request with proper authentication
            response = requests.get(url, **request_kwargs)

            # Raise exception if request failed
            response.raise_for_status()

            # Parse the response
            data = response.json()

            # Extract relevant deployment information
            deployments = []
            for row in data.get("rows", []):
                cells = row.get("cells", [])

                # exemple de contenu pour cells
                # [ NAME, READY, UP-TO-DATE, AVAILABLE, AGE, CONTAINER, IMAGE, LABELS ]
                # ['coredns', '0/0', 0, 0, '21h', 'coredns', 'registry.k8s.io/coredns/coredns:v1.11.3', 'k8s-app=kube-dns']

                # Get the namespace either from metadata object or use the provided namespace
                ns_value = ns or row.get("object", {}).get(
                    "metadata", {}).get("namespace")

                name = cells[0]  # First cell is the name

                # Parse replicas from the Ready column (format is typically "1/1")
                # Format: "ready/total" (e.g., "3/3")
                ready_str = cells[1]
                current_replicas = int(ready_str.split('/')[1])

                # Create a minimal deployment object with only what we need
                deployment = {
                    "metadata": {
                        "name": name,
                        "namespace": ns_value
                    },
                    "spec": {
                        "replicas": current_replicas
                    },
                    "is_minimal": True  # Flag to indicate this is a minimal object
                }

                deployments.append(deployment)

            logger.debug(
                f"Retrieved {len(deployments)} deployments with minimal data")
            return deployments

        except (requests.RequestException, json.JSONDecodeError) as e:
            logger.warning(f"Error listing deployments with minimal data: {e}")
            logger.info("Falling back to standard API call")

            # Fall back to standard API call if the minimal approach fails
            try:
                if ns:
                    deployments = self.api.list_namespaced_deployment(ns).items
                else:
                    deployments = self.api.list_deployment_for_all_namespaces().items

                # Convert to simplified format
                return [
                    {
                        "metadata": {
                            "name": d.metadata.name,
                            "namespace": d.metadata.namespace
                        },
                        "spec": {
                            "replicas": d.spec.replicas
                        },
                        "is_minimal": False
                    }
                    for d in deployments
                ]
            except Exception as e2:
                logger.error(f"Error in fallback API call: {e2}")
                # Return empty list rather than raising exception
                return []

    def _ensure_full_deployment_object(self, deployment: dict[str, Any] | client.V1Deployment) -> client.V1Deployment:
        """Ensure we have a full deployment object for operations that need it.

        Args:
            deployment: Either a minimal deployment dict or full V1Deployment object

        Returns:
            A full V1Deployment object
        """
        # If it's already a V1Deployment, return it
        if isinstance(deployment, client.V1Deployment):
            return deployment

        # If it's our minimal object, fetch the full deployment
        if isinstance(deployment, dict) and deployment.get("is_minimal", False):
            name = deployment["metadata"]["name"]
            namespace = deployment["metadata"]["namespace"]
            return self._get_deployment_light(name, namespace)

        # Otherwise convert the dict to a V1Deployment object
        return client.V1Deployment(
            metadata=client.V1ObjectMeta(
                name=deployment["metadata"]["name"],
                namespace=deployment["metadata"]["namespace"]
            ),
            spec=client.V1DeploymentSpec(
                replicas=deployment["spec"]["replicas"]
            )
        )

    def create_event(
        self,
        deployment: dict[str, Any] | client.V1Deployment,
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
            # Ensure we have a full deployment object
            full_deployment = self._ensure_full_deployment_object(deployment)

            # Use datetime with timezone info instead of utcnow
            now = datetime.now(UTC)

            # Initialize the event body
            body = client.EventsV1Event(
                metadata=client.V1ObjectMeta(
                    generate_name=f"{full_deployment.metadata.name}-",
                    namespace=full_deployment.metadata.namespace
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
                    name=full_deployment.metadata.name,
                    namespace=full_deployment.metadata.namespace,
                    uid=full_deployment.metadata.uid if hasattr(
                        full_deployment.metadata, 'uid') else None
                ),
                event_time=now
            )

            # Create the event in the Kubernetes API
            self.events_api.create_namespaced_event(
                namespace=full_deployment.metadata.namespace,
                body=body
            )
            logger.debug(
                f"Created event for deployment {full_deployment.metadata.namespace}/{full_deployment.metadata.name}: {reason}")

        except Exception as e:
            name = deployment["metadata"]["name"] if isinstance(
                deployment, dict) else deployment.metadata.name
            namespace = deployment["metadata"]["namespace"] if isinstance(
                deployment, dict) else deployment.metadata.namespace
            logger.warning(
                f"Failed to create event for deployment {namespace}/{name}: {e}"
            )

    def save_deployment_state(self, deployment: dict[str, Any] | client.V1Deployment) -> None:
        """Save the current replica count for a deployment.

        Stores the replica count in both an annotation on the deployment
        and in the memory cache as a fallback.

        Args:
            deployment: The deployment object to save the state for.
        """
        # Get basic info from either dict or V1Deployment
        if isinstance(deployment, dict):
            name = deployment["metadata"]["name"]
            namespace = deployment["metadata"]["namespace"]
            replicas = deployment["spec"]["replicas"]
        else:
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
            # Need to fetch the full deployment if we're working with a minimal object
            if isinstance(deployment, dict) and deployment.get("is_minimal", False):
                full_deployment = self._get_deployment_light(name, namespace)
            else:
                full_deployment = deployment

            # Update the deployment with the new annotation
            self.api.patch_namespaced_deployment(
                name=name,
                namespace=namespace,
                body={"metadata": {"annotations": {
                    TARNFUI_REPLICAS_ANNOTATION: str(replicas)}}}
            )
            logger.debug(
                f"Saved state for deployment {key} in annotation: {replicas} replicas")
        except Exception as e:
            logger.warning(
                f"Failed to save state in annotation for deployment {key}: {e}")
            logger.info(f"State saved in memory only: {replicas} replicas")

    def get_original_replicas(self, deployment: dict[str, Any] | client.V1Deployment) -> int | None:
        """Get the original replica count for a deployment.

        Tries to retrieve from annotations first, falls back to in-memory cache.

        Args:
            deployment: The deployment to get the original replica count for.

        Returns:
            The original replica count, or None if not found.
        """
        # Get basic info from either dict or V1Deployment
        if isinstance(deployment, dict):
            name = deployment["metadata"]["name"]
            namespace = deployment["metadata"]["namespace"]
        else:
            name = deployment.metadata.name
            namespace = deployment.metadata.namespace

        key = f"{namespace}/{name}"

        # Try from memory cache first to avoid an API call
        if key in self.deployment_replicas:
            replicas = self.deployment_replicas[key]
            logger.debug(
                f"Retrieved original replicas from memory cache for {key}: {replicas}")
            return replicas

        # We need to check annotations which requires the full object
        try:
            # Need to fetch the full deployment if we're working with a minimal object
            if isinstance(deployment, dict) and deployment.get("is_minimal", False):
                full_deployment = self._get_deployment_light(name, namespace)
            else:
                full_deployment = deployment

            # Try to get from annotations
            if (hasattr(full_deployment.metadata, 'annotations') and
                    full_deployment.metadata.annotations and
                    TARNFUI_REPLICAS_ANNOTATION in full_deployment.metadata.annotations):
                try:
                    replicas = int(
                        full_deployment.metadata.annotations[TARNFUI_REPLICAS_ANNOTATION])
                    logger.debug(
                        f"Retrieved original replicas from annotation for {key}: {replicas}")
                    return replicas
                except (ValueError, TypeError) as e:
                    logger.warning(
                        f"Invalid replica count in annotation for {key}: {e}")
        except Exception as e:
            logger.warning(
                f"Error getting annotations for deployment {key}: {e}")

        logger.warning(f"No saved state found for deployment {key}")
        return None

    def scale_deployment(self, deployment: dict[str, Any] | client.V1Deployment, replicas: int) -> None:
        """Scale a deployment to the specified number of replicas.

        Args:
            deployment: The deployment object to scale.
            replicas: The number of replicas to scale to.
        """
        # Get basic info from either dict or V1Deployment
        if isinstance(deployment, dict):
            name = deployment["metadata"]["name"]
            namespace = deployment["metadata"]["namespace"]
            current_replicas = deployment["spec"]["replicas"]
        else:
            name = deployment.metadata.name
            namespace = deployment.metadata.namespace
            current_replicas = deployment.spec.replicas

        logger.debug(
            f"Scaling deployment {namespace}/{name} to {replicas} replicas")

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
            current_replicas = deployment["spec"]["replicas"]
            if current_replicas == 0:
                continue

            self.scale_deployment(deployment, 0)
            logger.info(
                f"Stopped deployment {deployment["metadata"]["namespace"]}/{deployment["metadata"]["name"]}"
            )

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
            current_replicas = deployment["spec"]["replicas"]
            if current_replicas > 0:
                continue

            original_replicas = self.get_original_replicas(deployment)

            if original_replicas is not None and original_replicas > 0:
                self.scale_deployment(deployment, original_replicas)
                name = deployment["metadata"]["name"]
                namespace = deployment["metadata"]["namespace"]
                logger.info(
                    f"Restored deployment {namespace}/{name} to {original_replicas} replicas"
                )

        logger.info(
            f"Completed processing {len(deployments)} deployments.")
