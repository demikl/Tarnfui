"""Kubernetes CronJob handling module.

This module provides specific functionality for managing Kubernetes CronJobs.
"""

import logging

from kubernetes import client

from tarnfui.kubernetes.base import KubernetesResource
from tarnfui.kubernetes.connection import KubernetesConnection

logger = logging.getLogger(__name__)


class CronJobResource(KubernetesResource[client.V1CronJob]):
    """Handler for Kubernetes CronJob resources."""

    # Resource type specific constants
    RESOURCE_API_VERSION = "batch/v1"
    RESOURCE_KIND = "CronJob"

    def __init__(self, connection: KubernetesConnection, namespace: str | None = None):
        """Initialize the CronJob resource handler.

        Args:
            connection: The Kubernetes connection to use
            namespace: Optional namespace to filter resources. If None, all namespaces will be used.
        """
        super().__init__(connection, namespace)
        # API client for cronjobs
        self.api = connection.batch_v1_api

    def get_resource(self, name: str, namespace: str) -> client.V1CronJob:
        """Get a specific cronjob by name.

        Args:
            name: Name of the cronjob.
            namespace: Namespace of the cronjob.

        Returns:
            The cronjob object.
        """
        return self.api.read_namespaced_cron_job(name, namespace)

    def patch_resource(self, resource: client.V1CronJob, body: dict) -> None:
        """Patch a cronjob with the given body.

        Args:
            resource: The cronjob to patch.
            body: The patch body to apply.
        """
        self.api.patch_namespaced_cron_job(
            name=resource.metadata.name,
            namespace=resource.metadata.namespace,
            body=body,
        )

    def list_namespaced_resources(self, namespace: str, **kwargs) -> any:
        """List cronjobs in a specific namespace.

        Args:
            namespace: The namespace to list cronjobs in.
            **kwargs: Additional arguments to pass to the API call.

        Returns:
            The API response containing the list of cronjobs.
        """
        return self.api.list_namespaced_cron_job(namespace, **kwargs)

    def list_all_namespaces_resources(self, **kwargs) -> any:
        """List cronjobs across all namespaces.

        Args:
            **kwargs: Additional arguments to pass to the API call.

        Returns:
            The API response containing the list of cronjobs.
        """
        return self.api.list_cron_job_for_all_namespaces(**kwargs)

    def get_current_state(self, resource: client.V1CronJob) -> bool:
        """Get the current state of a cronjob.

        For CronJobs, the state is represented by whether the job is suspended.
        False means the job is active, True means it's suspended.

        Args:
            resource: The resource to get the state from.

        Returns:
            The current suspension state (False = active, True = suspended)
        """
        return resource.spec.suspend or False

    def suspend_resource(self, resource: client.V1CronJob) -> None:
        """Suspend a CronJob by setting suspend flag to True.

        Args:
            resource: The resource to suspend.
        """
        self.patch_resource(
            resource=resource,
            body={"spec": {"suspend": True}},
        )

    def resume_resource(self, resource: client.V1CronJob, saved_state: bool) -> None:
        """Resume a CronJob by restoring its suspend state.

        Args:
            resource: The resource to resume.
            saved_state: The saved state to restore (True = was suspended, False = was active).
        """
        # Restore the CronJob to its original state before Tarnfui suspended it
        # If saved_state is True, the CronJob was already suspended before Tarnfui,
        # so we should keep it suspended.
        # If saved_state is False, the CronJob was active before Tarnfui,
        # so we should reactivate it.
        self.patch_resource(
            resource=resource,
            body={"spec": {"suspend": saved_state}},
        )

    def is_suspended(self, resource: client.V1CronJob) -> bool:
        """Check if a cronjob is currently suspended.

        Args:
            resource: The resource to check.

        Returns:
            True if the resource is suspended, False otherwise.
        """
        return resource.spec.suspend or False

    def convert_state_from_string(self, state_str: str) -> bool:
        """Convert a state string from annotation to boolean.

        Args:
            state_str: The state string from the annotation.

        Returns:
            The state as a boolean (True = suspended, False = active).
        """
        return state_str.lower() == "true"
