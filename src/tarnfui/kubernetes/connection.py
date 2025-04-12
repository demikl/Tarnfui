"""Kubernetes connection management.

This module handles the connection to the Kubernetes API.
"""
import logging
import os
import socket

from kubernetes import client, config

logger = logging.getLogger(__name__)


class KubernetesConnection:
    """Connection manager for the Kubernetes API.

    This class manages authentication and connection to the Kubernetes API.
    It is shared among all resource handlers to avoid duplication of connection logic.
    """

    def __init__(self):
        """Initialize the Kubernetes connection.

        Attempts to connect to the Kubernetes API using in-cluster config first,
        falling back to kubeconfig for local development.
        """
        self._setup_connection()
        # Get hostname for event reporting
        self.hostname = socket.gethostname()
        # Unique identifier for this instance
        self.instance_id = os.environ.get("HOSTNAME", self.hostname)

    def _setup_connection(self) -> None:
        """Set up the connection to the Kubernetes API."""
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

        # Initialize API clients
        self.apps_v1_api = client.AppsV1Api()
        self.core_v1_api = client.CoreV1Api()
        self.events_v1_api = client.EventsV1Api()

        # Setup for direct API access if needed
        self.api_client = self.apps_v1_api.api_client
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
