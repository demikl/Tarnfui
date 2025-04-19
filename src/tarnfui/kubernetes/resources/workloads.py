"""Kubernetes Workload resources handling module.

This module provides common functionality for Kubernetes workload resources
such as Deployments and StatefulSets that can be scaled via replicas.
"""

import abc
import logging
from typing import Generic, TypeVar

from kubernetes.client.exceptions import ApiException

from tarnfui.kubernetes.base import KubernetesResource

logger = logging.getLogger(__name__)

# Type variable for workload resource types
T = TypeVar("T")


class ReplicatedWorkloadResource(KubernetesResource[T], Generic[T], abc.ABC):
    """Base class for Kubernetes resources that use replicas for scaling.

    This serves as a common base class for workload resources like
    Deployments and StatefulSets that share similar behavior.
    """

    def get_replicas(self, resource: T) -> int:
        """Get the current replica count for a resource.

        Args:
            resource: The resource to get the replica count from.

        Returns:
            The current replica count.
        """
        return resource.spec.replicas or 0

    def set_replicas(self, resource: T, replicas: int) -> None:
        """Set the replica count for a resource.

        Args:
            resource: The resource to set the replica count for.
            replicas: The number of replicas to set.
        """
        try:
            self.patch_resource(
                resource=resource,
                body={"spec": {"replicas": replicas}},
            )
        except ApiException as e:
            logger.error(
                f"Error setting replicas for {self.RESOURCE_KIND} "
                f"{resource.metadata.namespace}/{resource.metadata.name}: {e}"
            )
            raise

    @abc.abstractmethod
    def patch_resource(self, resource: T, body: dict) -> None:
        """Patch a specific resource with the given body.

        Args:
            resource: The resource to patch.
            body: The patch body to apply.
        """
        pass

    def get_current_state(self, resource: T) -> int:
        """Get the current state of a resource.

        For replicated workloads, the state is represented by the replica count.

        Args:
            resource: The resource to get the state from.

        Returns:
            The current replica count.
        """
        return self.get_replicas(resource)

    def suspend_resource(self, resource: T) -> None:
        """Suspend a resource by setting replicas to 0.

        Args:
            resource: The resource to suspend.
        """
        self.set_replicas(resource, 0)

    def resume_resource(self, resource: T, saved_state: int) -> None:
        """Resume a resource by restoring its replica count.

        Args:
            resource: The resource to resume.
            saved_state: The saved replica count to restore.
        """
        self.set_replicas(resource, saved_state)

    def is_suspended(self, resource: T) -> bool:
        """Check if a resource is currently suspended.

        A replicated resource is considered suspended if it has 0 replicas.

        Args:
            resource: The resource to check.

        Returns:
            True if the resource is suspended (has 0 replicas), False otherwise.
        """
        return self.get_replicas(resource) == 0

    @abc.abstractmethod
    def list_namespaced_resources(self, namespace: str, **kwargs) -> any:
        """List resources in a specific namespace.

        Args:
            namespace: The namespace to list resources in.
            **kwargs: Additional arguments to pass to the API call.

        Returns:
            The API response containing the list of resources.
        """
        pass

    @abc.abstractmethod
    def list_all_namespaces_resources(self, **kwargs) -> any:
        """List resources across all namespaces.

        Args:
            **kwargs: Additional arguments to pass to the API call.

        Returns:
            The API response containing the list of resources.
        """
        pass
