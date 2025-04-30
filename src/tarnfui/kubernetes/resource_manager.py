"""Resource Manager for Kubernetes resources.

This module provides the ResourceManager base class for Kubernetes resources
that can manage other resources.
"""

import abc
import logging
from functools import lru_cache
from typing import Any, ClassVar, Generic, Optional, TypeVar

from tarnfui.kubernetes.base import KubernetesResource
from tarnfui.kubernetes.connection import KubernetesConnection
from tarnfui.kubernetes.resources.events import create_restoration_event, create_suspension_event

logger = logging.getLogger(__name__)

# Type variable for resource types
T = TypeVar("T")


class ResourceManager(KubernetesResource[T], Generic[T], abc.ABC):
    """Base class for Kubernetes resources that can manage other resources.

    This class represents resources that have a management relationship with other resources.
    When a resource of this type is stopped or started, the resources it manages should be
    stopped or started accordingly.
    """

    # Maximum size of the LRU cache
    _LRU_CACHE_SIZE: ClassVar[int] = 100

    @classmethod
    def find_manager_for_resource(cls, resource: Any, connection: KubernetesConnection) -> Optional["ResourceManager"]:
        """Find a manager of this class that manages the given resource.

        This class method is called during resource reconciliation to determine if a resource
        is managed by a resource of this type.

        Args:
            resource: The resource to check if it's managed.
            connection: The Kubernetes connection to use for queries.

        Returns:
            An instance of this ResourceManager subclass if it manages the resource,
            None otherwise.
        """
        # Default implementation returns None, subclasses should override
        return None

    @classmethod
    @lru_cache(maxsize=_LRU_CACHE_SIZE)
    def is_manager_processed(cls, manager_key: str) -> bool:
        """Check if a manager has already been processed.

        This method uses the lru_cache decorator to keep track of which manager
        instances have been processed during a reconciliation cycle.

        Args:
            manager_key: A unique key for the manager.

        Returns:
            True if the manager has already been processed, False otherwise.
        """
        return True  # If in cache, return True

    @classmethod
    def mark_manager_processed(cls, manager_key: str) -> None:
        """Mark a manager as already processed.

        This method adds the manager key to the LRU cache to avoid processing
        the same manager multiple times during a reconciliation cycle.

        Args:
            manager_key: A unique key for the manager.
        """
        # Simply call is_manager_processed to cache the result
        cls.is_manager_processed(manager_key)

    @classmethod
    def clear_processed_managers(cls) -> None:
        """Clear the processed managers cache.

        This should be called after each reconciliation cycle.
        """
        cls.is_manager_processed.cache_clear()

    def process_manager_resource(self, resource: Any, is_stopping: bool = True) -> bool:
        """Process a resource manager for a given resource.

        This helper method handles the common logic for processing a manager resource,
        either when stopping or starting resources.

        Args:
            resource: The resource being processed
            is_stopping: Whether we are stopping (True) or starting (False) resources

        Returns:
            True if the manager was processed, False if it was already processed
        """
        # Generate a unique key for this manager
        manager_key = self.get_resource_key(resource)

        # Skip if we've already processed this manager
        if self.__class__.is_manager_processed(manager_key):
            return False

        # Get manager details for logging
        manager_name = self.get_resource_name(resource)
        manager_namespace = self.get_resource_namespace(resource)

        # Mark as processed to avoid reprocessing
        self.__class__.mark_manager_processed(manager_key)

        if is_stopping:
            # Get current state and suspend the manager if it's not already suspended
            manager_state = self.get_current_state(resource)
            if manager_state is not None and not self.is_suspended(resource):
                # Save current state before suspending
                self.save_resource_state(resource)
                self.suspend_resource(resource)

                # Create event for the manager
                message = (
                    f"Resource was suspended by Tarnfui during non-working hours as it manages other resources. "
                    f"Original state: {manager_state}"
                )
                event_creator = create_suspension_event
            else:
                # Manager already suspended or has no state
                return True
        else:
            # Get saved state and restore the manager
            manager_saved_state = self.get_saved_state(resource)
            if manager_saved_state is not None:
                self.resume_resource(resource, manager_saved_state)

                # Create event for the manager
                message = (
                    f"Resource was restored by Tarnfui during working hours. Restored state: {manager_saved_state}"
                )
                event_creator = create_restoration_event
            else:
                # No saved state for manager
                return True

        # Create the appropriate event
        try:
            event_creator(
                connection=self.connection,
                resource=resource,
                api_version=self.__class__.RESOURCE_API_VERSION,
                kind=self.__class__.RESOURCE_KIND,
                message=message,
            )
            logger.debug(f"Created event for manager {self.__class__.RESOURCE_KIND} {manager_namespace}/{manager_name}")
        except Exception as event_error:
            logger.warning(
                f"Failed to create event for manager {self.__class__.RESOURCE_KIND} {manager_namespace}/{manager_name}: {event_error}"
            )

        return True
