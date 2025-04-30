"""Base module for Kubernetes resources.

This module provides base classes for all Kubernetes resources.
"""

import abc
import logging
from collections.abc import Iterator
from typing import Any, ClassVar, Generic, TypeVar

from tarnfui.kubernetes.connection import KubernetesConnection
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
        if isinstance(resource, dict):
            return resource.get("metadata", {}).get("name", "")
        return resource.metadata.name

    def get_resource_namespace(self, resource: T) -> str:
        """Get the namespace of a resource.

        Args:
            resource: The resource to get the namespace for.

        Returns:
            The namespace of the resource.
        """
        if isinstance(resource, dict):
            return resource.get("metadata", {}).get("namespace", "")
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
        metadata = resource.get("metadata", {}) if isinstance(resource, dict) else resource.metadata
        annotations = (
            metadata.get("annotations", {}) if isinstance(metadata, dict) else getattr(metadata, "annotations", {})
        )
        return annotations.get(annotation_key)

    def _process_manager_if_exists(self, resource: T, is_stopping: bool) -> None:
        """Process a resource manager for a resource if one exists.

        This helper method handles finding and processing a manager resource.

        Args:
            resource: The resource to find a manager for
            is_stopping: Whether we're stopping (True) or starting (False) resources
        """
        # Check if this resource is managed by a ResourceManager
        manager_type, manager_name, manager_namespace = self._find_resource_manager(resource)
        if manager_type:
            # Use the ResourceManager's process_manager method instead of directly checking/marking
            action = "stopping" if is_stopping else "starting"
            logger.info(
                f"Found manager {manager_type.__class__.RESOURCE_KIND} {manager_namespace}/{manager_name} "
                f"for {self.RESOURCE_KIND} {self.get_resource_namespace(resource)}/{self.get_resource_name(resource)} "
                f"while {action} resources"
            )

            try:
                # a resource manager typically manages multiple resources
                # but we only need to process it once
                if not self._should_process_resource_by_name_namespace(manager_name, manager_namespace, is_stopping):
                    return

                # Get the actual manager resource
                manager_resource = manager_type.get_resource(manager_name, manager_namespace)

                # Process the manager using _process_resource to avoid code duplication
                manager_type._process_resource(manager_resource, is_stopping)

            except Exception as e:
                logger.error(
                    f"Error processing manager {manager_type.__class__.RESOURCE_KIND} {manager_namespace}/{manager_name}: {e}"
                )

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

    def _should_process_resource(self, resource: T, is_stopping: bool) -> bool:
        """Check if a resource should be processed.

        Args:
            resource: The resource to check

        Returns:
            True if the resource should be processed, False otherwise
        """
        # Default implementation, override in subclasses for resource-specific logic
        return True

    def _should_process_resource_by_name_namespace(self, name: str, namespace: str, is_stopping: bool) -> bool:
        """Check if a resource should be processed.

        Args:
            name: The name of the resource to check
            namespace: The namespace of the resource to check
            is_stopping: True if stopping the resource, False if starting

        Returns:
            True if the resource should be processed, False otherwise
        """
        # Default implementation, override in subclasses for resource-specific logic
        return True

    def _process_resource(self, resource: T, is_stopping: bool) -> bool:
        """Process a single resource for stopping or starting.

        Args:
            resource: The resource to process
            is_stopping: True if stopping the resource, False if starting

        Returns:
            True if the resource was processed (stopped/started), False otherwise
        """
        # First, check if this resource has a manager that needs to be processed first
        self._process_manager_if_exists(resource, is_stopping=is_stopping)

        name = self.get_resource_name(resource)
        namespace = self.get_resource_namespace(resource)

        if is_stopping:
            # Process for stopping: check if not suspended and suspend
            current_state = self.get_current_state(resource)
            if current_state is not None and not self.is_suspended(resource):
                # Save the current state and suspend the resource
                self.save_resource_state(resource)
                self.suspend_resource(resource)

                # Create an event for the suspended resource
                self._create_resource_event(resource, current_state, is_suspension=True)

                logger.info(
                    f"Suspended {self.RESOURCE_KIND} {namespace}/{name} and stored initial state: {current_state}"
                )
                return True
        else:
            # Process for starting: check if suspended and resume
            if self.is_suspended(resource):
                # Get the saved state for this resource
                saved_state = self.get_saved_state(resource)
                if saved_state is not None:
                    # Restore this resource
                    self.resume_resource(resource, saved_state)

                    # Create an event for the restored resource
                    self._create_resource_event(resource, saved_state, is_suspension=False)

                    logger.info(f"Restored {self.RESOURCE_KIND} {namespace}/{name} to previous state: {saved_state}")
                    return True

        return False

    def _process_resources(self, namespace: str | None, batch_size: int, is_stopping: bool) -> tuple[int, int]:
        """Common logic for processing resources in batches.

        Args:
            namespace: Namespace to process resources in
            batch_size: Number of resources to process per batch
            is_stopping: True if stopping resources, False if starting

        Returns:
            Tuple of (total_processed, total_affected)
        """
        total_processed = 0
        total_affected = 0

        try:
            # Process resources in a streaming fashion
            for resource in self.iter_resources(namespace=namespace, batch_size=batch_size):
                total_processed += 1

                # Process the resource and track if it was affected
                if self._should_process_resource(resource, is_stopping) and self._process_resource(
                    resource, is_stopping
                ):
                    total_affected += 1

            # Clear the manager cache after processing all resources
            # Avoid circular import by importing here
            from tarnfui.kubernetes.resource_manager import ResourceManager

            ResourceManager.clear_processed_managers()

        except Exception as e:
            action = "stopping" if is_stopping else "starting"
            logger.error(f"Error {action} {self.RESOURCE_KIND}s: {e}")

        return total_processed, total_affected

    def stop_resources(self, namespace: str | None = None, batch_size: int = 100) -> None:
        """Suspend all resources.

        Args:
            namespace: Namespace to stop resources in. If None, use the handler's namespace.
            batch_size: Number of resources to process per batch.
        """
        ns = namespace or self.namespace
        logger.info(f"Initiating the process to stop {self.RESOURCE_KIND}s")

        total_processed, total_stopped = self._process_resources(ns, batch_size, is_stopping=True)

        logger.info(
            f"Completed processing {total_processed} {self.RESOURCE_KIND}s. "
            f"Stopped {total_stopped} {self.RESOURCE_KIND}s."
        )

    def start_resources(self, namespace: str | None = None, batch_size: int = 100) -> None:
        """Resume all resources.

        Args:
            namespace: Namespace to start resources in. If None, use the handler's namespace.
            batch_size: Number of resources to process per batch.
        """
        ns = namespace or self.namespace
        logger.info(f"Starting to restore {self.RESOURCE_KIND}s")

        total_processed, total_started = self._process_resources(ns, batch_size, is_stopping=False)

        logger.info(
            f"Completed processing {total_processed} {self.RESOURCE_KIND}s. "
            f"Started {total_started} {self.RESOURCE_KIND}s."
        )

    def is_suspended(self, resource: T) -> bool:
        """Check if a resource is currently suspended.

        Args:
            resource: The resource to check.

        Returns:
            True if the resource is suspended, False otherwise.
        """
        # Default implementation, override in subclasses for resource-specific logic
        return False

    def _find_resource_manager(self, resource: T) -> tuple["ResourceManager | None", str | None, str | None]:
        """Find a resource manager for this resource if one exists.

        This method attempts to find a manager for this resource by checking all
        registered ResourceManager subclasses.

        Args:
            resource: The resource to find a manager for.

        Returns:
            A tuple containing:
            - An instance of a ResourceManager if found, None otherwise
            - The name of the manager resource, or None if no manager was found
            - The namespace of the manager resource, or None if no manager was found
        """
        # Avoid circular import by importing here
        from tarnfui.kubernetes.resource_manager import ResourceManager

        # Check each ResourceManager subclass to see if it manages this resource
        for manager_class in ResourceManager.__subclasses__():
            result = manager_class.find_manager_for_resource(resource, self.connection)
            if result:
                manager, name, namespace = result
                return manager, name, namespace
        return None, None, None
