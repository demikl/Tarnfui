"""Base module for Kubernetes resources.

This module provides base classes for all Kubernetes resources.
"""

import abc
import logging
from typing import ClassVar, Generic, TypeVar

from tarnfui.kubernetes.connection import KubernetesConnection

logger = logging.getLogger(__name__)

# Type variable for resource types
T = TypeVar("T")


class KubernetesResource(Generic[T], abc.ABC):
    """Base class for all Kubernetes resources.

    This abstract base class defines the common interface and functionality
    for all Kubernetes resources that can be managed by Tarnfui.
    """

    # Key used for storing replica count in resource annotations
    REPLICA_ANNOTATION: ClassVar[str] = "tarnfui.io/original-replicas"

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
        # Dictionary to store the original replica counts for resources
        self._memory_state: dict[str, int] = {}

    @abc.abstractmethod
    def get_resources(self, namespace: str | None = None, batch_size: int = 100) -> list[T]:
        """Get all resources of this type.

        Args:
            namespace: Namespace to get resources from. If None, use the handler's namespace.
            batch_size: Number of resources to fetch per API call.

        Returns:
            List of resources of this type.
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
    def get_replicas(self, resource: T) -> int:
        """Get the current replica count for a resource.

        Args:
            resource: The resource to get the replica count from.

        Returns:
            The current replica count.
        """
        pass

    @abc.abstractmethod
    def set_replicas(self, resource: T, replicas: int) -> None:
        """Set the replica count for a resource.

        Args:
            resource: The resource to set the replica count for.
            replicas: The number of replicas to set.
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
        """Save the current replica count for a resource.

        This method stores the replica count in both an annotation on the resource
        and in the memory cache as a fallback.

        Args:
            resource: The resource to save the state for.
        """
        replicas = self.get_replicas(resource)
        name = self.get_resource_name(resource)
        namespace = self.get_resource_namespace(resource)

        if replicas <= 0:
            logger.debug(f"Skipping save for {self.RESOURCE_KIND} {namespace}/{name} with 0 replicas")
            return

        key = self.get_resource_key(resource)

        # Save in memory as a fallback
        self._memory_state[key] = replicas

        try:
            # Try to save the state in an annotation
            self._save_annotation(resource, self.REPLICA_ANNOTATION, str(replicas))
            logger.debug(f"Saved state for {self.RESOURCE_KIND} {key} in annotation: {replicas} replicas")
        except Exception as e:
            logger.warning(f"Failed to save state in annotation for {self.RESOURCE_KIND} {key}: {e}")
            logger.info(f"State saved in memory only: {replicas} replicas")

    @abc.abstractmethod
    def _save_annotation(self, resource: T, annotation_key: str, annotation_value: str) -> None:
        """Save an annotation on a resource.

        Args:
            resource: The resource to annotate.
            annotation_key: The annotation key.
            annotation_value: The annotation value.
        """
        pass

    def get_original_replicas(self, resource: T) -> int | None:
        """Get the original replica count for a resource.

        Tries to retrieve from annotations first, falls back to in-memory cache.

        Args:
            resource: The resource to get the original replica count for.

        Returns:
            The original replica count, or None if not found.
        """
        key = self.get_resource_key(resource)

        # Try from memory cache first to avoid an API call
        if key in self._memory_state:
            replicas = self._memory_state[key]
            logger.debug(f"Retrieved original replicas from memory cache for {key}: {replicas}")
            return replicas

        # Try to get from annotations
        try:
            annotation_value = self._get_annotation(resource, self.REPLICA_ANNOTATION)
            if annotation_value:
                try:
                    replicas = int(annotation_value)
                    logger.debug(f"Retrieved original replicas from annotation for {key}: {replicas}")
                    return replicas
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid replica count in annotation for {key}: {e}")
        except Exception as e:
            logger.warning(f"Error getting annotations for {self.RESOURCE_KIND} {key}: {e}")

        logger.warning(f"No saved state found for {self.RESOURCE_KIND} {key}")
        return None

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

    def scale(self, resource: T, replicas: int) -> None:
        """Scale a resource to the specified number of replicas.

        This method handles saving the current state if scaling to zero.

        Args:
            resource: The resource to scale.
            replicas: The number of replicas to scale to.
        """
        name = self.get_resource_name(resource)
        namespace = self.get_resource_namespace(resource)
        current_replicas = self.get_replicas(resource)

        logger.debug(f"Scaling {self.RESOURCE_KIND} {namespace}/{name} to {replicas} replicas")

        # Save the current state if scaling to zero
        if replicas == 0 and current_replicas > 0:
            self.save_resource_state(resource)

            # Generate a scaling event
            from tarnfui.kubernetes.resources.events import create_scaling_event

            create_scaling_event(
                connection=self.connection,
                resource=resource,
                api_version=self.RESOURCE_API_VERSION,
                kind=self.RESOURCE_KIND,
                event_type="Normal",
                reason="Stopped",
                message=f"Scaled down {self.RESOURCE_KIND} from {current_replicas} to 0 replicas by Tarnfui",
            )

        # Generate a scaling event when scaling up
        elif replicas > 0 and current_replicas == 0:
            from tarnfui.kubernetes.resources.events import create_scaling_event

            create_scaling_event(
                connection=self.connection,
                resource=resource,
                api_version=self.RESOURCE_API_VERSION,
                kind=self.RESOURCE_KIND,
                event_type="Normal",
                reason="Started",
                message=f"Scaled up {self.RESOURCE_KIND} from 0 to {replicas} replicas by Tarnfui",
            )

        # Apply the new scale
        self.set_replicas(resource, replicas)

    def stop_resources(self, namespace: str | None = None, batch_size: int = 100) -> None:
        """Scale all resources to zero replicas.

        Args:
            namespace: Namespace to stop resources in. If None, use the handler's namespace.
            batch_size: Number of resources to process per batch.
        """
        ns = namespace or self.namespace
        logger.info(f"Starting to stop {self.RESOURCE_KIND}s")

        total_processed = 0
        total_stopped = 0

        try:
            resources = self.get_resources(namespace=ns, batch_size=batch_size)
            total_processed = len(resources)

            for resource in resources:
                # Skip resources that are already scaled to 0
                if self.get_replicas(resource) == 0:
                    continue

                self.scale(resource, 0)
                total_stopped += 1
                name = self.get_resource_name(resource)
                namespace = self.get_resource_namespace(resource)
                logger.info(f"Stopped {self.RESOURCE_KIND} {namespace}/{name}")

            logger.info(
                f"Completed processing {total_processed} {self.RESOURCE_KIND}s. "
                f"Stopped {total_stopped} {self.RESOURCE_KIND}s."
            )

        except Exception as e:
            logger.error(f"Error stopping {self.RESOURCE_KIND}s: {e}")

    def start_resources(self, namespace: str | None = None, batch_size: int = 100) -> None:
        """Restore all resources to their original replica counts.

        Args:
            namespace: Namespace to start resources in. If None, use the handler's namespace.
            batch_size: Number of resources to process per batch.
        """
        ns = namespace or self.namespace
        logger.info(f"Starting to restore {self.RESOURCE_KIND}s")

        total_processed = 0
        total_started = 0

        try:
            resources = self.get_resources(namespace=ns, batch_size=batch_size)
            total_processed = len(resources)

            for resource in resources:
                # Only restore resources that are currently scaled to 0
                if self.get_replicas(resource) > 0:
                    continue

                # Get the original replicas for this resource
                original_replicas = self.get_original_replicas(resource)

                if original_replicas is not None and original_replicas > 0:
                    self.scale(resource, original_replicas)
                    total_started += 1
                    name = self.get_resource_name(resource)
                    namespace = self.get_resource_namespace(resource)
                    logger.info(f"Restored {self.RESOURCE_KIND} {namespace}/{name} to {original_replicas} replicas")

            logger.info(
                f"Completed processing {total_processed} {self.RESOURCE_KIND}s. "
                f"Started {total_started} {self.RESOURCE_KIND}s."
            )

        except Exception as e:
            logger.error(f"Error starting {self.RESOURCE_KIND}s: {e}")
