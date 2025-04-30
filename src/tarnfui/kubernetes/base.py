"""Base module for Kubernetes resources.

This module provides base classes for all Kubernetes resources.
"""

import abc
import logging
from collections.abc import Iterator
from typing import Any, ClassVar, Generic, TypeVar

from tarnfui.kubernetes.connection import KubernetesConnection
from tarnfui.kubernetes.resource_manager import ResourceManager
from tarnfui.kubernetes.resources.events import create_restoration_event, create_suspension_event

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

    def iter_resources(self, namespace: str | None = None, batch_size: int = 100) -> Iterator[T]:
        """Iterate over all resources in a namespace or across all namespaces.

        Uses pagination to fetch resources in batches and yield them one by one
        to limit memory usage.

        Args:
            namespace: Namespace to get resources from. If None, use the handler's namespace.
            batch_size: Number of resources to fetch per API call.

        Yields:
            Resources, one at a time.
        """
        ns = namespace or self.namespace
        continue_token = None

        try:
            while True:
                # Fetch current page of resources
                if ns:
                    result = self.list_namespaced_resources(ns, limit=batch_size, _continue=continue_token)
                else:
                    result = self.list_all_namespaces_resources(limit=batch_size, _continue=continue_token)

                # Yield resources from this page one by one
                yield from result.items

                # Check if there are more pages to process
                continue_token = result.metadata._continue
                if not continue_token:
                    break

        except Exception as e:
            logger.error(f"Error getting {self.RESOURCE_KIND}s: {e}")
            return

    @abc.abstractmethod
    def list_namespaced_resources(self, namespace: str, **kwargs) -> Any:
        """List resources in a specific namespace.

        Args:
            namespace: The namespace to list resources in.
            **kwargs: Additional arguments to pass to the API call.

        Returns:
            The API response containing the list of resources.
        """
        pass

    @abc.abstractmethod
    def list_all_namespaces_resources(self, **kwargs) -> Any:
        """List resources across all namespaces.

        Args:
            **kwargs: Additional arguments to pass to the API call.

        Returns:
            The API response containing the list of resources.
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

    def get_resource_key(self, resource: T) -> str:
        """Get a unique key for a resource.

        Args:
            resource: The resource to get the key for.

        Returns:
            A string that uniquely identifies the resource.
        """
        return f"{self.get_resource_namespace(resource)}/{self.get_resource_name(resource)}"

    def get_resource_name(self, resource: T) -> str:
        """Get the name of a resource.

        Args:
            resource: The resource to get the name for.

        Returns:
            The name of the resource.
        """
        return resource.metadata.name

    def get_resource_namespace(self, resource: T) -> str:
        """Get the namespace of a resource.

        Args:
            resource: The resource to get the namespace for.

        Returns:
            The namespace of the resource.
        """
        return resource.metadata.namespace

    def save_resource_state(self, resource: T) -> None:
        """Save the current state for a resource.

        This method stores the state in both an annotation on the resource
        and in the memory cache as a fallback.

        Args:
            resource: The resource to save the state for.
        """
        current_state = self.get_current_state(resource)
        key = self.get_resource_key(resource)

        # Save in memory as a fallback
        self._memory_state[key] = current_state

        try:
            # Try to save the state in an annotation
            # Convert state to string for storage in annotation
            state_str = str(current_state)
            self._save_annotation(resource, self.STATE_ANNOTATION, state_str)
            logger.debug(f"Saved state for {self.RESOURCE_KIND} {key} in annotation: {state_str}")
        except Exception as e:
            logger.warning(f"Failed to save state in annotation for {self.RESOURCE_KIND} {key}: {e}")
            logger.info(f"State saved in memory only: {current_state}")

    def _save_annotation(self, resource: T, annotation_key: str, annotation_value: str) -> None:
        """Save an annotation on a resource.

        Args:
            resource: The resource to annotate.
            annotation_key: The annotation key.
            annotation_value: The annotation value.
        """
        try:
            # Use the patch_resource method to apply the annotation
            self.patch_resource(
                resource=resource,
                body={"metadata": {"annotations": {annotation_key: annotation_value}}},
            )
        except Exception as e:
            logger.error(
                f"Error saving annotation for {self.RESOURCE_KIND} "
                f"{self.get_resource_namespace(resource)}/{self.get_resource_name(resource)}: {e}"
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
            logger.debug(f"Retrieved saved state from memory cache for {key}: {state}")
            return state

        # Try to get from annotations
        try:
            annotation_value = self._get_annotation(resource, self.STATE_ANNOTATION)
            if annotation_value is not None:
                try:
                    # Convert based on resource type (implementations should handle this)
                    state = self.convert_state_from_string(annotation_value)
                    logger.debug(f"Retrieved saved state from annotation for {key}: {state}")
                    return state
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid state in annotation for {key}: {e}")
        except Exception as e:
            logger.warning(f"Error getting annotations for {self.RESOURCE_KIND} {key}: {e}")

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
            if state_str.lower() in ("true", "false"):
                return state_str.lower() == "true"
            # Otherwise return as string
            return state_str

    def _get_annotation(self, resource: T, annotation_key: str) -> str | None:
        """Get an annotation from a resource.

        Args:
            resource: The resource to get the annotation from.
            annotation_key: The annotation key to get.

        Returns:
            The annotation value, or None if not found.
        """
        if (
            hasattr(resource.metadata, "annotations")
            and resource.metadata.annotations
            and annotation_key in resource.metadata.annotations
        ):
            return resource.metadata.annotations[annotation_key]
        return None

    def _process_manager_if_exists(self, resource: T, is_stopping: bool) -> None:
        """Process a resource manager for a resource if one exists.

        This helper method handles finding and processing a manager resource.

        Args:
            resource: The resource to find a manager for
            is_stopping: Whether we're stopping (True) or starting (False) resources
        """
        # Check if this resource is managed by a ResourceManager
        manager = self._find_resource_manager(resource)
        if manager:
            # If a manager is found, process it first
            manager_key = manager.get_resource_key()

            # Skip if we've already processed this manager
            if not manager.__class__.is_manager_processed(manager_key):
                manager_name = manager.get_resource_name()
                manager_namespace = manager.get_resource_namespace()

                action = "stopping" if is_stopping else "starting"
                logger.info(
                    f"Found manager {manager.__class__.RESOURCE_KIND} {manager_namespace}/{manager_name} "
                    f"for {self.RESOURCE_KIND} {self.get_resource_namespace(resource)}/{self.get_resource_name(resource)} "
                    f"while {action} resources"
                )

                # Process the manager using its own logic
                manager.process_manager_resource(is_stopping)

    def _create_resource_event(self, resource: T, state: Any, is_suspension: bool) -> None:
        """Create a suspension or restoration event for a resource.

        Args:
            resource: The resource to create an event for
            state: The state to include in the event message
            is_suspension: True to create a suspension event, False for restoration
        """
        name = self.get_resource_name(resource)
        namespace = self.get_resource_namespace(resource)

        if is_suspension:
            message = f"Resource was suspended by Tarnfui during non-working hours. Original state: {state}"
            event_creator = create_suspension_event
            event_type = "suspension"
        else:
            message = f"Resource was restored by Tarnfui during working hours. Restored state: {state}"
            event_creator = create_restoration_event
            event_type = "restoration"

        try:
            event_creator(
                connection=self.connection,
                resource=resource,
                api_version=self.RESOURCE_API_VERSION,
                kind=self.RESOURCE_KIND,
                message=message,
            )
            logger.debug(f"Created {event_type} event for {self.RESOURCE_KIND} {namespace}/{name}")
        except Exception as event_error:
            logger.warning(
                f"Failed to create {event_type} event for {self.RESOURCE_KIND} {namespace}/{name}: {event_error}"
            )

    def stop_resources(self, namespace: str | None = None, batch_size: int = 100) -> None:
        """Suspend all resources.

        Args:
            namespace: Namespace to stop resources in. If None, use the handler's namespace.
            batch_size: Number of resources to process per batch.
        """
        ns = namespace or self.namespace
        logger.info(f"Initiating the process to stop {self.RESOURCE_KIND}s")

        total_processed = 0
        total_stopped = 0

        try:
            # Process resources in a streaming fashion
            for resource in self.iter_resources(namespace=ns, batch_size=batch_size):
                total_processed += 1

                # First, check if this resource has a manager that needs to be suspended first
                self._process_manager_if_exists(resource, is_stopping=True)

                # Now process this resource
                current_state = self.get_current_state(resource)
                if current_state is not None and not self.is_suspended(resource):
                    # Save the current state and suspend the resource
                    self.save_resource_state(resource)
                    self.suspend_resource(resource)

                    # Create an event for the suspended resource
                    self._create_resource_event(resource, current_state, is_suspension=True)

                    total_stopped += 1
                    name = self.get_resource_name(resource)
                    namespace = self.get_resource_namespace(resource)
                    logger.info(f"Stopped {self.RESOURCE_KIND} {namespace}/{name}")
                # if the resource should be ignored, tell why in verbose mode
                elif self.is_suspended(resource):
                    name = self.get_resource_name(resource)
                    namespace = self.get_resource_namespace(resource)
                    logger.debug(f"Skipping {self.RESOURCE_KIND} {namespace}/{name} as it is already suspended")
                else:
                    name = self.get_resource_name(resource)
                    namespace = self.get_resource_namespace(resource)
                    logger.debug(f"Skipping {self.RESOURCE_KIND} {namespace}/{name} as current state is None")

            logger.info(
                f"Completed processing {total_processed} {self.RESOURCE_KIND}s. "
                f"Stopped {total_stopped} {self.RESOURCE_KIND}s."
            )

            # Clear the manager cache after processing all resources
            ResourceManager.clear_processed_managers()

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
                    # Check if this resource has a manager that needs to be restored first
                    self._process_manager_if_exists(resource, is_stopping=False)

                    # Now restore this resource
                    self.resume_resource(resource, saved_state)

                    # Create an event for the restored resource
                    self._create_resource_event(resource, saved_state, is_suspension=False)

                    total_started += 1
                    name = self.get_resource_name(resource)
                    namespace = self.get_resource_namespace(resource)
                    logger.info(f"Restored {self.RESOURCE_KIND} {namespace}/{name} to previous state: {saved_state}")

            logger.info(
                f"Completed processing {total_processed} {self.RESOURCE_KIND}s. "
                f"Started {total_started} {self.RESOURCE_KIND}s."
            )

            # Clear the manager cache after processing all resources
            ResourceManager.clear_processed_managers()

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

    def _find_resource_manager(self, resource: T) -> ResourceManager | None:
        """Find a resource manager for this resource if one exists.

        This method attempts to find a manager for this resource by checking all
        registered ResourceManager subclasses.

        Args:
            resource: The resource to find a manager for.

        Returns:
            An instance of a ResourceManager if found, None otherwise.
        """
        # Check each ResourceManager subclass to see if it manages this resource
        for manager_class in ResourceManager.__subclasses__():
            manager = manager_class.find_manager_for_resource(resource, self.connection)
            if manager:
                return manager
        return None
