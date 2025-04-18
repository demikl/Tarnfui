"""Base module for Kubernetes resources.

This module provides base classes for all Kubernetes resources.
"""

import abc
import logging
from collections.abc import Iterator
from typing import Any, ClassVar, Generic, TypeVar

from tarnfui.kubernetes.connection import KubernetesConnection

logger = logging.getLogger(__name__)

# Type variable for resource types
T = TypeVar("T")


class KubernetesResource(Generic[T], abc.ABC):
    """Base class for all Kubernetes resources.

    This abstract base class defines the common interface and functionality
    for all Kubernetes resources that can be managed by Tarnfui.
    """

    # Key used for storing resource state in annotations
    STATE_ANNOTATION: ClassVar[str] = "tarnfui.io/original-state"

    # Resource type specific constants
    RESOURCE_API_VERSION: ClassVar[str]
    RESOURCE_KIND: ClassVar[str]

    def __init__(self, connection: KubernetesConnection, namespace: str | None = None):
        """Initialize the resource handler.

        Args:
            connection: The Kubernetes connection to use
            namespace: Optional namespace to filter resources. If None, all namespaces will be used.
        """
        self.connection = connection
        self.namespace = namespace
        # Dictionary to store the original state for resources
        self._memory_state: dict[str, Any] = {}

    @abc.abstractmethod
    def iter_resources(self, namespace: str | None = None, batch_size: int = 100) -> Iterator[T]:
        """Iterate over all resources of this type.

        This method returns an iterator that yields resources one by one,
        fetching them in batches to limit memory usage and API load.

        Args:
            namespace: Namespace to get resources from. If None, use the handler's namespace.
            batch_size: Number of resources to fetch per API call.

        Yields:
            Resources of this type, one at a time.
        """
        pass

    @abc.abstractmethod
    def get_resource(self, name: str, namespace: str) -> T:
        """Get a specific resource by name.

        Args:
            name: Name of the resource.
            namespace: Namespace of the resource.

        Returns:
            The resource object.
        """
        pass

    @abc.abstractmethod
    def get_current_state(self, resource: T) -> Any:
        """Get the current state of a resource.

        For different resource types, this will return different types of state:
        - For Deployments: returns the replica count (int)
        - For Kustomizations: returns whether it is suspended (bool)

        Args:
            resource: The resource to get the state from.

        Returns:
            The current state, type depends on the resource.
        """
        pass

    @abc.abstractmethod
    def suspend_resource(self, resource: T) -> None:
        """Suspend a resource.

        Resource-specific implementation of suspending the resource:
        - For Deployments: sets replicas to 0
        - For Kustomizations: sets spec.suspend to true

        Args:
            resource: The resource to suspend.
        """
        pass

    @abc.abstractmethod
    def resume_resource(self, resource: T, saved_state: Any) -> None:
        """Resume a resource with its saved state.

        Resource-specific implementation of resuming the resource:
        - For Deployments: restores the replica count
        - For Kustomizations: sets spec.suspend to false

        Args:
            resource: The resource to resume.
            saved_state: The previously saved state to restore.
        """
        pass

    @abc.abstractmethod
    def get_resource_key(self, resource: T) -> str:
        """Get a unique key for a resource.

        Args:
            resource: The resource to get the key for.

        Returns:
            A string that uniquely identifies the resource.
        """
        pass

    @abc.abstractmethod
    def get_resource_name(self, resource: T) -> str:
        """Get the name of a resource.

        Args:
            resource: The resource to get the name for.

        Returns:
            The name of the resource.
        """
        pass

    @abc.abstractmethod
    def get_resource_namespace(self, resource: T) -> str:
        """Get the namespace of a resource.

        Args:
            resource: The resource to get the namespace for.

        Returns:
            The namespace of the resource.
        """
        pass

    def save_resource_state(self, resource: T) -> None:
        """Save the current state for a resource.

        This method stores the state in both an annotation on the resource
        and in the memory cache as a fallback.

        Args:
            resource: The resource to save the state for.
        """
        current_state = self.get_current_state(resource)
        name = self.get_resource_name(resource)
        namespace = self.get_resource_namespace(resource)
        key = self.get_resource_key(resource)

        # Save in memory as a fallback
        self._memory_state[key] = current_state

        try:
            # Try to save the state in an annotation
            # Convert state to string for storage in annotation
            state_str = str(current_state)
            self._save_annotation(resource, self.STATE_ANNOTATION, state_str)
            logger.debug(
                f"Saved state for {self.RESOURCE_KIND} {key} in annotation: {state_str}")
        except Exception as e:
            logger.warning(
                f"Failed to save state in annotation for {self.RESOURCE_KIND} {key}: {e}")
            logger.info(f"State saved in memory only: {current_state}")

    @abc.abstractmethod
    def _save_annotation(self, resource: T, annotation_key: str, annotation_value: str) -> None:
        """Save an annotation on a resource.

        Args:
            resource: The resource to annotate.
            annotation_key: The annotation key.
            annotation_value: The annotation value.
        """
        pass

    def get_saved_state(self, resource: T) -> Any | None:
        """Get the saved state for a resource.

        Tries to retrieve from memory cache first, falls back to annotations.

        Args:
            resource: The resource to get the saved state for.

        Returns:
            The saved state, or None if not found.
        """
        key = self.get_resource_key(resource)

        # Try from memory cache first to avoid an API call
        if key in self._memory_state:
            state = self._memory_state[key]
            logger.debug(
                f"Retrieved saved state from memory cache for {key}: {state}")
            return state

        # Try to get from annotations
        try:
            annotation_value = self._get_annotation(
                resource, self.STATE_ANNOTATION)
            if annotation_value is not None:
                try:
                    # Convert based on resource type (implementations should handle this)
                    state = self.convert_state_from_string(annotation_value)
                    logger.debug(
                        f"Retrieved saved state from annotation for {key}: {state}")
                    return state
                except (ValueError, TypeError) as e:
                    logger.warning(
                        f"Invalid state in annotation for {key}: {e}")
        except Exception as e:
            logger.warning(
                f"Error getting annotations for {self.RESOURCE_KIND} {key}: {e}")

        logger.warning(f"No saved state found for {self.RESOURCE_KIND} {key}")
        return None

    def convert_state_from_string(self, state_str: str) -> Any:
        """Convert a state string from annotation to the proper type.

        Args:
            state_str: The state string from the annotation.

        Returns:
            The state value in its proper type.
        """
        # Default implementation (override in subclasses as needed)
        try:
            # Try to convert to int first (for deployments)
            return int(state_str)
        except ValueError:
            # Try to convert to boolean
            if state_str.lower() in ('true', 'false'):
                return state_str.lower() == 'true'
            # Otherwise return as string
            return state_str

    @abc.abstractmethod
    def _get_annotation(self, resource: T, annotation_key: str) -> str | None:
        """Get an annotation from a resource.

        Args:
            resource: The resource to get the annotation from.
            annotation_key: The annotation key to get.

        Returns:
            The annotation value, or None if not found.
        """
        pass

    def stop_resources(self, namespace: str | None = None, batch_size: int = 100) -> None:
        """Suspend all resources.

        Args:
            namespace: Namespace to stop resources in. If None, use the handler's namespace.
            batch_size: Number of resources to process per batch.
        """
        ns = namespace or self.namespace
        logger.info(f"Starting to stop {self.RESOURCE_KIND}s")

        total_processed = 0
        total_stopped = 0

        try:
            # Process resources in a streaming fashion
            for resource in self.iter_resources(namespace=ns, batch_size=batch_size):
                total_processed += 1

                # Save current state and suspend the resource
                current_state = self.get_current_state(resource)
                if current_state is not None and not self.is_suspended(resource):
                    self.save_resource_state(resource)
                    self.suspend_resource(resource)
                    total_stopped += 1
                    name = self.get_resource_name(resource)
                    namespace = self.get_resource_namespace(resource)
                    logger.info(
                        f"Stopped {self.RESOURCE_KIND} {namespace}/{name}")

            logger.info(
                f"Completed processing {total_processed} {self.RESOURCE_KIND}s. "
                f"Stopped {total_stopped} {self.RESOURCE_KIND}s."
            )

        except Exception as e:
            logger.error(f"Error stopping {self.RESOURCE_KIND}s: {e}")

    def start_resources(self, namespace: str | None = None, batch_size: int = 100) -> None:
        """Resume all resources.

        Args:
            namespace: Namespace to start resources in. If None, use the handler's namespace.
            batch_size: Number of resources to process per batch.
        """
        ns = namespace or self.namespace
        logger.info(f"Starting to restore {self.RESOURCE_KIND}s")

        total_processed = 0
        total_started = 0

        try:
            # Process resources in a streaming fashion
            for resource in self.iter_resources(namespace=ns, batch_size=batch_size):
                total_processed += 1

                # Only restore resources that are currently suspended
                if not self.is_suspended(resource):
                    continue

                # Get the saved state for this resource
                saved_state = self.get_saved_state(resource)

                if saved_state is not None:
                    self.resume_resource(resource, saved_state)
                    total_started += 1
                    name = self.get_resource_name(resource)
                    namespace = self.get_resource_namespace(resource)
                    logger.info(
                        f"Restored {self.RESOURCE_KIND} {namespace}/{name} to previous state")

            logger.info(
                f"Completed processing {total_processed} {self.RESOURCE_KIND}s. "
                f"Started {total_started} {self.RESOURCE_KIND}s."
            )

        except Exception as e:
            logger.error(f"Error starting {self.RESOURCE_KIND}s: {e}")

    def is_suspended(self, resource: T) -> bool:
        """Check if a resource is currently suspended.

        Args:
            resource: The resource to check.

        Returns:
            True if the resource is suspended, False otherwise.
        """
        # Default implementation, override in subclasses for resource-specific logic
        return False
