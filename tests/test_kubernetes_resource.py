"""Tests for the Kubernetes resource base module."""

import unittest
from collections.abc import Iterator
from typing import Any, ClassVar
from unittest import mock

from tarnfui.kubernetes.base import KubernetesResource
from tarnfui.kubernetes.connection import KubernetesConnection


# Mock concrete implementation of KubernetesResource for testing
class MockKubernetesResource(KubernetesResource[dict]):
    """Mock implementation of KubernetesResource for testing."""

    RESOURCE_API_VERSION: ClassVar[str] = "v1"
    RESOURCE_KIND: ClassVar[str] = "MockResource"

    def __init__(self, connection: KubernetesConnection, namespace: str | None = None):
        """Initialize the mock resource."""
        super().__init__(connection, namespace)
        self.suspended_resources = set()  # Track suspended resources
        self.patch_calls = []  # Track patch calls

    def iter_resources(self, namespace: str | None = None, batch_size: int = 100) -> Iterator[dict]:
        """Mock implementation of iter_resources."""
        resources = [{"metadata": {"name": f"resource-{i}", "namespace": namespace or "default"}} for i in range(3)]
        yield from resources

    def get_resource(self, name: str, namespace: str) -> dict:
        """Mock implementation of get_resource."""
        return {"metadata": {"name": name, "namespace": namespace}}

    def get_current_state(self, resource: dict) -> Any:
        """Mock implementation of get_current_state."""
        resource_key = self.get_resource_key(resource)
        return 0 if resource_key in self.suspended_resources else 3

    def suspend_resource(self, resource: dict) -> None:
        """Mock implementation of suspend_resource."""
        self.suspended_resources.add(self.get_resource_key(resource))

    def resume_resource(self, resource: dict, saved_state: Any) -> None:
        """Mock implementation of resume_resource."""
        resource_key = self.get_resource_key(resource)
        if resource_key in self.suspended_resources:
            self.suspended_resources.remove(resource_key)

    def get_resource_key(self, resource: dict) -> str:
        """Mock implementation of get_resource_key."""
        return f"{resource['metadata']['namespace']}/{resource['metadata']['name']}"

    def get_resource_name(self, resource: dict) -> str:
        """Mock implementation of get_resource_name."""
        return resource["metadata"]["name"]

    def get_resource_namespace(self, resource: dict) -> str:
        """Mock implementation of get_resource_namespace."""
        return resource["metadata"]["namespace"]

    def patch_resource(self, resource: dict, body: dict) -> None:
        """Mock implementation of patch_resource."""
        # Track the patch call for verification in tests
        self.patch_calls.append({"resource": resource, "body": body})

        # Apply the changes to the resource (simple implementation for testing)
        if "metadata" in body and "annotations" in body["metadata"]:
            if "annotations" not in resource["metadata"]:
                resource["metadata"]["annotations"] = {}
            resource["metadata"]["annotations"].update(body["metadata"]["annotations"])

    def _get_annotation(self, resource: dict, annotation_key: str) -> str | None:
        """Mock implementation of _get_annotation."""
        if "metadata" in resource and "annotations" in resource["metadata"]:
            return resource["metadata"]["annotations"].get(annotation_key)
        return None

    def is_suspended(self, resource: dict) -> bool:
        """Mock implementation of is_suspended."""
        return self.get_resource_key(resource) in self.suspended_resources

    def list_namespaced_resources(self, namespace: str, **kwargs) -> any:
        """Mock implementation of list_namespaced_resources."""
        resources = [{"metadata": {"name": f"resource-{i}", "namespace": namespace}} for i in range(3)]
        return mock.Mock(items=resources, metadata=mock.Mock(_continue=None))

    def list_all_namespaces_resources(self, **kwargs) -> any:
        """Mock implementation of list_all_namespaces_resources."""
        resources = [{"metadata": {"name": f"resource-{i}", "namespace": f"ns-{i}"}} for i in range(3)]
        return mock.Mock(items=resources, metadata=mock.Mock(_continue=None))


class TestKubernetesResource(unittest.TestCase):
    """Test cases for the KubernetesResource class."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock the KubernetesConnection
        self.connection_mock = mock.Mock(spec=KubernetesConnection)

        # Create the resource handler
        self.namespace = "test-namespace"
        self.resource = MockKubernetesResource(self.connection_mock, self.namespace)

        # Patch create_suspension_event and create_restoration_event functions
        self.create_suspension_event_patcher = mock.patch("tarnfui.kubernetes.base.create_suspension_event")
        self.create_suspension_event_mock = self.create_suspension_event_patcher.start()

        self.create_restoration_event_patcher = mock.patch("tarnfui.kubernetes.base.create_restoration_event")
        self.create_restoration_event_mock = self.create_restoration_event_patcher.start()

    def tearDown(self):
        """Tear down test fixtures."""
        self.create_suspension_event_patcher.stop()
        self.create_restoration_event_patcher.stop()

    def test_init_with_namespace(self):
        """Test that the resource is initialized with a namespace."""
        self.assertEqual(self.resource.namespace, self.namespace)
        self.assertEqual(self.resource.connection, self.connection_mock)
        self.assertEqual(self.resource._memory_state, {})

    def test_save_resource_state_memory(self):
        """Test saving resource state to memory."""
        # Create a test resource
        resource = {"metadata": {"name": "test-resource", "namespace": self.namespace}}

        # Mock get_current_state to return a specific value
        self.resource.get_current_state = mock.Mock(return_value=5)

        # Save the resource state
        self.resource.save_resource_state(resource)

        # Verify that the state was saved in memory
        resource_key = self.resource.get_resource_key(resource)
        self.assertIn(resource_key, self.resource._memory_state)
        self.assertEqual(self.resource._memory_state[resource_key], 5)

    def test_save_resource_state_annotation(self):
        """Test saving resource state to annotations."""
        # Create a test resource with annotations
        resource = {"metadata": {"name": "test-resource", "namespace": self.namespace, "annotations": {}}}

        # Mock get_current_state to return a specific value
        self.resource.get_current_state = mock.Mock(return_value=5)

        # Save the resource state
        self.resource.save_resource_state(resource)

        # Verify that _save_annotation was called with the correct parameters
        self.assertEqual(resource["metadata"]["annotations"][KubernetesResource.STATE_ANNOTATION], "5")

    def test_get_saved_state_from_memory(self):
        """Test getting saved state from memory."""
        # Create a test resource
        resource = {"metadata": {"name": "test-resource", "namespace": self.namespace}}
        resource_key = self.resource.get_resource_key(resource)

        # Set a state in memory
        expected_state = 5
        self.resource._memory_state[resource_key] = expected_state

        # Get the saved state
        state = self.resource.get_saved_state(resource)

        # Verify that the correct state was returned
        self.assertEqual(state, expected_state)

    def test_get_saved_state_from_annotation(self):
        """Test getting saved state from annotations."""
        # Create a test resource with an annotation
        resource = {
            "metadata": {
                "name": "test-resource",
                "namespace": self.namespace,
                "annotations": {KubernetesResource.STATE_ANNOTATION: "5"},
            }
        }

        # Get the saved state
        state = self.resource.get_saved_state(resource)

        # Verify that the correct state was returned
        self.assertEqual(state, 5)

    def test_convert_state_from_string(self):
        """Test converting state from string to proper type."""
        # Test converting to int
        self.assertEqual(self.resource.convert_state_from_string("5"), 5)

        # Test converting to boolean
        self.assertEqual(self.resource.convert_state_from_string("true"), True)
        self.assertEqual(self.resource.convert_state_from_string("false"), False)

        # Test converting to string
        self.assertEqual(self.resource.convert_state_from_string("test"), "test")

    def test_stop_resources(self):
        """Test stopping resources."""
        # Create a list of test resources
        resources = [{"metadata": {"name": f"resource-{i}", "namespace": self.namespace}} for i in range(3)]

        # Mock iter_resources to return these resources
        self.resource.iter_resources = mock.Mock(return_value=iter(resources))

        # Stop the resources
        self.resource.stop_resources(self.namespace)

        # Verify that save_resource_state and suspend_resource were called for each resource
        self.assertEqual(len(self.resource.suspended_resources), 3)
        self.create_suspension_event_mock.assert_called()

    def test_start_resources(self):
        """Test starting resources."""
        # Create a list of test resources
        resources = [{"metadata": {"name": f"resource-{i}", "namespace": self.namespace}} for i in range(3)]

        # Mark these resources as suspended
        for resource in resources:
            self.resource.suspended_resources.add(self.resource.get_resource_key(resource))

        # Mock iter_resources to return these resources
        self.resource.iter_resources = mock.Mock(return_value=iter(resources))

        # Mock get_saved_state to return a non-None value
        self.resource.get_saved_state = mock.Mock(return_value=3)

        # Start the resources
        self.resource.start_resources(self.namespace)

        # Verify that all resources were resumed
        self.assertEqual(len(self.resource.suspended_resources), 0)
        self.create_restoration_event_mock.assert_called()

    def test_start_resources_no_saved_state(self):
        """Test starting resources with no saved state."""
        # Create a list of test resources
        resources = [{"metadata": {"name": f"resource-{i}", "namespace": self.namespace}} for i in range(3)]

        # Mark these resources as suspended
        for resource in resources:
            self.resource.suspended_resources.add(self.resource.get_resource_key(resource))

        # Mock iter_resources to return these resources
        self.resource.iter_resources = mock.Mock(return_value=iter(resources))

        # Mock get_saved_state to return None
        self.resource.get_saved_state = mock.Mock(return_value=None)

        # Start the resources
        self.resource.start_resources(self.namespace)

        # Verify that resume_resource was not called (since there's no saved state)
        self.assertEqual(len(self.resource.suspended_resources), 3)
        self.create_restoration_event_mock.assert_not_called()

    def test_is_suspended(self):
        """Test checking if a resource is suspended."""
        # Create a test resource
        resource = {"metadata": {"name": "test-resource", "namespace": self.namespace}}

        # Verify that the resource is not suspended initially
        self.assertFalse(self.resource.is_suspended(resource))

        # Suspend the resource
        self.resource.suspended_resources.add(self.resource.get_resource_key(resource))

        # Verify that the resource is now suspended
        self.assertTrue(self.resource.is_suspended(resource))


if __name__ == "__main__":
    unittest.main()
