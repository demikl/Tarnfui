"""Resource Manager for Kubernetes resources.

This module provides the ResourceManager base class for Kubernetes resources
that can manage other resources.
"""

import abc
import logging
from collections import OrderedDict
from typing import Any, ClassVar, Generic, TypeVar

from tarnfui.kubernetes.base import KubernetesResource
from tarnfui.kubernetes.connection import KubernetesConnection

logger = logging.getLogger(__name__)

# Type variable for resource types
T = TypeVar("T")


class ResourceManager(KubernetesResource[T], Generic[T], abc.ABC):
    """Base class for Kubernetes resources that can manage other resources.

    This class represents resources that have a management relationship with other resources.
    When a resource of this type is stopped or started, the resources it manages should be
    stopped or started accordingly.
    """

    # Maximum size of the processed managers cache
    _PROCESSED_MANAGERS_MAX_SIZE: ClassVar[int] = 100

    # Class variable to track processed managers with OrderedDict for LRU behavior
    _processed_managers: ClassVar[OrderedDict[str, bool]] = OrderedDict()

    @classmethod
    def find_manager_for_resource(
        cls, resource: Any, connection: KubernetesConnection
    ) -> tuple["ResourceManager", str, str] | None:
        """Find a manager of this class that manages the given resource.

        This class method is called during resource reconciliation to determine if a resource
        is managed by a resource of this type.

        Args:
            resource: The resource to check if it's managed.
            connection: The Kubernetes connection to use for queries.

        Returns:
            A tuple containing:
              - An instance of this ResourceManager subclass if it manages the resource
              - The name of the manager resource
              - The namespace of the manager resource
            or None if no manager is found
        """
        # Default implementation returns None, subclasses should override
        return None

    def _should_process_resource_by_name_namespace(self, name, namespace, is_stopping):
        return self.__class__.is_manager_processed(name, namespace)

    @classmethod
    def is_manager_processed(cls, name: str, namespace: str) -> bool:
        """Check if a manager resource has already been processed.

        This method checks if the manager resource has already been processed during
        the current reconciliation cycle.

        Args:
            name: The name of the manager resource.
            namespace: The namespace of the manager resource.

        Returns:
            True if the resource has already been processed, False otherwise.
        """
        return cls.manager_key(name, namespace) in cls._processed_managers

    @classmethod
    def mark_manager_processed(cls, name: str, namespace: str) -> None:
        """Mark a manager as already processed.

        This method adds the manager resource ref to the processed managers cache to avoid processing
        the same manager multiple times during a reconciliation cycle. It maintains LRU behavior
        by moving the accessed key to the end and removing the oldest item if necessary.

        Args:
            name: The name of the manager resource.
            namespace: The namespace of the manager resource.
        """
        # If the key exists, remove it so it can be added to the end (making it most recently used)
        manager_key = cls.manager_key(name, namespace)
        if manager_key in cls._processed_managers:
            cls._processed_managers.pop(manager_key)

        # Add the key to the end (most recently used position)
        cls._processed_managers[manager_key] = True

        # If we exceeded the max size, remove the oldest item (first in the OrderedDict)
        if len(cls._processed_managers) > cls._PROCESSED_MANAGERS_MAX_SIZE:
            cls._processed_managers.popitem(last=False)

    @classmethod
    def clear_processed_managers(cls) -> None:
        """Clear the processed managers cache.

        This should be called after each reconciliation cycle.
        """
        cls._processed_managers.clear()

    @classmethod
    def manager_key(cls, name: str, namespace: str) -> str:
        """Generate a unique key for the manager resource.

        This key is used to identify the manager resource in the processed managers cache.

        Args:
            name: The name of the manager resource.
            namespace: The namespace of the manager resource.

        Returns:
            A unique key for the manager resource.
        """
        return f"{name}/{namespace}"
