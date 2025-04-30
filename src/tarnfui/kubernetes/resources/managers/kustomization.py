"""Flux CD Kustomization resource manager.

This module provides implementation of ResourceManager for Flux CD Kustomization
resources that can manage other Kubernetes workloads.
"""

import logging
from typing import Any, ClassVar

from tarnfui.kubernetes.connection import KubernetesConnection
from tarnfui.kubernetes.resource_manager import ResourceManager

logger = logging.getLogger(__name__)


class Kustomization(ResourceManager[dict[str, Any]]):
    """Manages Flux CD Kustomization resources.

    Kustomization resources are custom resources from Flux CD that manage
    the deployment of other Kubernetes resources through GitOps.
    """

    RESOURCE_API_VERSION: ClassVar[str] = "kustomize.toolkit.fluxcd.io/v1"
    RESOURCE_KIND: ClassVar[str] = "Kustomization"

    def __init__(self, connection: KubernetesConnection, namespace: str | None = None):
        """Initialize the Kustomization manager.

        Args:
            connection: The Kubernetes connection to use
            namespace: Optional namespace to filter resources
        """
        super().__init__(connection, namespace)

    def get_resource(self, name: str, namespace: str) -> dict[str, Any]:
        """Get a specific Kustomization resource by name.

        Args:
            name: Name of the Kustomization
            namespace: Namespace of the Kustomization

        Returns:
            The Kustomization resource object
        """
        try:
            return self.connection.custom_objects_api.get_namespaced_custom_object(
                group="kustomize.toolkit.fluxcd.io",
                version="v1",
                namespace=namespace,
                plural="kustomizations",
                name=name,
            )
        except Exception as e:
            logger.error(f"Error getting Kustomization {namespace}/{name}: {e}")
            raise

    def list_namespaced_resources(self, namespace: str, **kwargs) -> Any:
        """List Kustomization resources in a namespace.

        Args:
            namespace: The namespace to list resources in
            **kwargs: Additional arguments to pass to the API call

        Returns:
            The API response containing Kustomization resources
        """
        return self.connection.custom_objects_api.list_namespaced_custom_object(
            group="kustomize.toolkit.fluxcd.io",
            version="v1",
            namespace=namespace,
            plural="kustomizations",
            **kwargs,
        )

    def list_all_namespaces_resources(self, **kwargs) -> Any:
        """List Kustomization resources across all namespaces.

        Args:
            **kwargs: Additional arguments to pass to the API call

        Returns:
            The API response containing Kustomization resources
        """
        return self.connection.custom_objects_api.list_cluster_custom_object(
            group="kustomize.toolkit.fluxcd.io",
            version="v1",
            plural="kustomizations",
            **kwargs,
        )

    def get_current_state(self, resource: dict[str, Any]) -> bool:
        """Get the current state of a Kustomization.

        For Kustomizations, the state is whether it's suspended or not.

        Args:
            resource: The Kustomization resource to get the state from

        Returns:
            Whether the Kustomization is suspended
        """
        return resource.get("spec", {}).get("suspend", False)

    def suspend_resource(self, resource: dict[str, Any]) -> None:
        """Suspend a Kustomization.

        This sets the spec.suspend field to True to prevent further
        synchronization of resources managed by this Kustomization.

        Args:
            resource: The Kustomization resource to suspend
        """
        self.patch_resource(resource, {"spec": {"suspend": True}})

    def resume_resource(self, resource: dict[str, Any], saved_state: Any) -> None:
        """Resume a Kustomization.

        This sets the spec.suspend field back to its original state.

        Args:
            resource: The Kustomization resource to resume
            saved_state: The saved state (boolean indicating previous suspension state)
        """
        # For Kustomizations, the saved state is a boolean
        suspend_value = False
        if isinstance(saved_state, bool):
            suspend_value = saved_state

        self.patch_resource(resource, {"spec": {"suspend": suspend_value}})

    def patch_resource(self, resource: dict[str, Any], body: dict) -> None:
        """Patch a Kustomization resource with the given body.

        Args:
            resource: The Kustomization resource to patch
            body: The patch body to apply
        """
        name = self.get_resource_name(resource)
        namespace = self.get_resource_namespace(resource)

        try:
            self.connection.custom_objects_api.patch_namespaced_custom_object(
                group="kustomize.toolkit.fluxcd.io",
                version="v1",
                namespace=namespace,
                plural="kustomizations",
                name=name,
                body=body,
            )
            logger.debug(f"Patched Kustomization {namespace}/{name}: {body}")
        except Exception as e:
            logger.error(f"Error patching Kustomization {namespace}/{name}: {e}")
            raise

    def is_suspended(self, resource: dict[str, Any]) -> bool:
        """Check if a Kustomization is suspended.

        Args:
            resource: The Kustomization resource to check

        Returns:
            True if the Kustomization is suspended, False otherwise
        """
        return resource.get("spec", {}).get("suspend", False)

    @classmethod
    def find_manager_for_resource(
        cls, resource: Any, connection: KubernetesConnection
    ) -> tuple["Kustomization", str, str] | None:
        """Find a Kustomization manager for a given resource.

        This checks if a resource is managed by a Flux Kustomization by
        examining the resource's labels.

        Args:
            resource: The resource to check if it's managed
            connection: The Kubernetes connection to use for queries

        Returns:
            A tuple containing (Kustomization instance, kustomization_name, kustomization_namespace)
            if a Kustomization manages this resource, None otherwise
        """
        # Check if the resource has the required metadata
        if (
            not hasattr(resource, "metadata")
            or not hasattr(resource.metadata, "labels")
            or not resource.metadata.labels
        ):
            return None

        # Flux adds these labels to resources it manages
        name_label = "kustomize.toolkit.fluxcd.io/name"
        namespace_label = "kustomize.toolkit.fluxcd.io/namespace"

        # Check if the resource has the Kustomization name label
        if name_label in resource.metadata.labels:
            kustomization_name = resource.metadata.labels[name_label]

            # Determine the namespace of the Kustomization
            # Use the explicit namespace label if available, otherwise use the resource's namespace
            if namespace_label in resource.metadata.labels:
                kustomization_namespace = resource.metadata.labels[namespace_label]
            else:
                kustomization_namespace = resource.metadata.namespace

            logger.debug(
                f"Found resource {resource.metadata.namespace}/{resource.metadata.name} managed by "
                f"Kustomization {kustomization_namespace}/{kustomization_name}"
            )

            # Create and return a Kustomization instance
            kustomization_manager = Kustomization(connection, kustomization_namespace)
            try:
                # Try to get the actual Kustomization resource to verify it exists
                kustomization_manager.get_resource(kustomization_name, kustomization_namespace)
                return (kustomization_manager, kustomization_name, kustomization_namespace)
            except Exception as e:
                logger.warning(f"Error finding Kustomization {kustomization_namespace}/{kustomization_name}: {e}")

        return None
