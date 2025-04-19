import unittest
from unittest.mock import MagicMock

from kubernetes.client.exceptions import ApiException

from tarnfui.kubernetes.connection import KubernetesConnection
from tarnfui.kubernetes.resources.workloads import ReplicatedWorkloadResource


# Create a concrete implementation of ReplicatedWorkloadResource for testing
class MockWorkloadResource(ReplicatedWorkloadResource):
    """Mock implementation of ReplicatedWorkloadResource for testing."""

    RESOURCE_API_VERSION = "mock/v1"
    RESOURCE_KIND = "MockWorkload"

    def __init__(self, connection: KubernetesConnection, namespace: str | None = None):
        """Initialize the mock workload resource handler."""
        super().__init__(connection, namespace)
        self.api = connection.mock_api

    def get_resource(self, name: str, namespace: str) -> any:
        """Get a specific mock resource by name."""
        return self.api.read_namespaced_resource(name, namespace)

    def patch_resource(self, resource: any, body: dict) -> None:
        """Patch a mock resource with the given body."""
        self.api.patch_namespaced_resource(
            name=resource.metadata.name,
            namespace=resource.metadata.namespace,
            body=body,
        )

    def list_namespaced_resources(self, namespace: str, **kwargs) -> any:
        """List mock resources in a specific namespace."""
        return self.api.list_namespaced_resource(namespace, **kwargs)

    def list_all_namespaces_resources(self, **kwargs) -> any:
        """List mock resources across all namespaces."""
        return self.api.list_resource_for_all_namespaces(**kwargs)


class TestReplicatedWorkloadResource(unittest.TestCase):
    """Unit tests for the ReplicatedWorkloadResource abstract class."""

    def setUp(self):
        """Set up test environment before each test method."""
        # Create a mock KubernetesConnection with the necessary attributes
        self.mock_connection = MagicMock(spec=KubernetesConnection)
        self.mock_connection.mock_api = MagicMock()
        self.workload_resource = MockWorkloadResource(self.mock_connection, namespace="default")

    def test_get_replicas(self):
        """Test getting the replica count from a workload resource."""
        # Setup mock resource with 3 replicas
        mock_resource = MagicMock()
        mock_resource.spec.replicas = 3

        # Execute the method
        replicas = self.workload_resource.get_replicas(mock_resource)

        # Assertions
        self.assertEqual(replicas, 3)

    def test_get_replicas_none(self):
        """Test getting replicas when the value is None."""
        # Setup mock resource with None replicas
        mock_resource = MagicMock()
        mock_resource.spec.replicas = None

        # Execute the method
        replicas = self.workload_resource.get_replicas(mock_resource)

        # Assertions
        self.assertEqual(replicas, 0)

    def test_set_replicas(self):
        """Test setting replicas for a workload resource."""
        # Setup mock resource
        mock_resource = MagicMock()
        mock_resource.metadata.name = "test-resource"
        mock_resource.metadata.namespace = "default"

        # Execute the method
        self.workload_resource.set_replicas(mock_resource, 3)

        # Assertions
        self.mock_connection.mock_api.patch_namespaced_resource.assert_called_once_with(
            name="test-resource", namespace="default", body={"spec": {"replicas": 3}}
        )

    def test_set_replicas_api_exception(self):
        """Test handling API exceptions when setting replicas."""
        # Setup mock resource
        mock_resource = MagicMock()
        mock_resource.metadata.name = "test-resource"
        mock_resource.metadata.namespace = "default"
        mock_resource.spec.replicas = 3

        # Configure mock API to raise an exception
        self.mock_connection.mock_api.patch_namespaced_resource.side_effect = ApiException(status=409)

        # Execute the method and check that the exception is propagated
        with self.assertRaises(ApiException):
            self.workload_resource.set_replicas(mock_resource, 5)

    def test_get_current_state(self):
        """Test getting the current state of a workload resource."""
        # Setup mock resource
        mock_resource = MagicMock()
        mock_resource.spec.replicas = 5

        # Execute the method
        state = self.workload_resource.get_current_state(mock_resource)

        # Assertions
        self.assertEqual(state, 5)

    def test_suspend_resource(self):
        """Test suspending a resource by setting replicas to 0."""
        # Setup mock resource
        mock_resource = MagicMock()
        mock_resource.metadata.name = "test-resource"
        mock_resource.metadata.namespace = "default"

        # Execute the method
        self.workload_resource.suspend_resource(mock_resource)

        # Assertions
        self.mock_connection.mock_api.patch_namespaced_resource.assert_called_once_with(
            name="test-resource", namespace="default", body={"spec": {"replicas": 0}}
        )

    def test_resume_resource(self):
        """Test resuming a resource by restoring replicas."""
        # Setup mock resource
        mock_resource = MagicMock()
        mock_resource.metadata.name = "test-resource"
        mock_resource.metadata.namespace = "default"

        # Execute the method
        self.workload_resource.resume_resource(mock_resource, 5)

        # Assertions
        self.mock_connection.mock_api.patch_namespaced_resource.assert_called_once_with(
            name="test-resource", namespace="default", body={"spec": {"replicas": 5}}
        )

    def test_is_suspended_true(self):
        """Test checking if a resource is suspended (0 replicas)."""
        # Setup mock resource with 0 replicas
        mock_resource = MagicMock()
        mock_resource.spec.replicas = 0

        # Execute the method
        is_suspended = self.workload_resource.is_suspended(mock_resource)

        # Assertions
        self.assertTrue(is_suspended)

    def test_is_suspended_false(self):
        """Test checking if a resource is not suspended (> 0 replicas)."""
        # Setup mock resource with > 0 replicas
        mock_resource = MagicMock()
        mock_resource.spec.replicas = 1

        # Execute the method
        is_suspended = self.workload_resource.is_suspended(mock_resource)

        # Assertions
        self.assertFalse(is_suspended)


if __name__ == "__main__":
    unittest.main()
