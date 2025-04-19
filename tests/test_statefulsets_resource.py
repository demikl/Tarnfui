"""Unit tests for the StatefulSetResource class."""

import unittest
from unittest.mock import MagicMock, patch

from kubernetes.client import V1StatefulSet

from tarnfui.kubernetes.connection import KubernetesConnection
from tarnfui.kubernetes.resources.statefulsets import StatefulSetResource


class TestStatefulSetResource(unittest.TestCase):
    """Unit tests for the StatefulSetResource class."""

    def setUp(self):
        """Set up test environment before each test method."""
        # Create a mock KubernetesConnection with the necessary attributes
        self.mock_connection = MagicMock(spec=KubernetesConnection)
        self.mock_connection.apps_v1_api = MagicMock()
        self.statefulset_resource = StatefulSetResource(self.mock_connection, namespace="default")

    @patch("tarnfui.kubernetes.resources.statefulsets.client.AppsV1Api")
    def test_iter_resources_with_namespace(self, mock_apps_v1_api):
        """Test listing statefulsets in a specific namespace."""
        # Setup mock statefulset
        mock_statefulset = MagicMock(spec=V1StatefulSet)
        mock_statefulset.metadata.name = "test-statefulset"
        mock_statefulset.metadata.namespace = "default"

        # Configure mock api response
        mock_result = MagicMock()
        mock_result.items = [mock_statefulset]
        mock_result.metadata._continue = None
        self.mock_connection.apps_v1_api.list_namespaced_stateful_set.return_value = mock_result

        # Execute the method
        statefulsets = list(self.statefulset_resource.iter_resources())

        # Assertions
        self.assertEqual(len(statefulsets), 1)
        self.assertEqual(statefulsets[0].metadata.name, "test-statefulset")
        self.mock_connection.apps_v1_api.list_namespaced_stateful_set.assert_called_once_with(
            "default", limit=100, _continue=None
        )

    @patch("tarnfui.kubernetes.resources.statefulsets.client.AppsV1Api")
    def test_iter_resources_all_namespaces(self, mock_apps_v1_api):
        """Test listing statefulsets across all namespaces."""
        # Setup mock statefulset
        mock_statefulset = MagicMock(spec=V1StatefulSet)
        mock_statefulset.metadata.name = "test-statefulset"
        mock_statefulset.metadata.namespace = "default"

        # Configure mock api response
        mock_result = MagicMock()
        mock_result.items = [mock_statefulset]
        mock_result.metadata._continue = None
        self.mock_connection.apps_v1_api.list_stateful_set_for_all_namespaces.return_value = mock_result

        # Create a resource handler without namespace filter
        all_ns_resource = StatefulSetResource(self.mock_connection, namespace=None)

        # Execute the method
        statefulsets = list(all_ns_resource.iter_resources())

        # Assertions
        self.assertEqual(len(statefulsets), 1)
        self.assertEqual(statefulsets[0].metadata.name, "test-statefulset")
        self.mock_connection.apps_v1_api.list_stateful_set_for_all_namespaces.assert_called_once_with(
            limit=100, _continue=None
        )

    @patch("tarnfui.kubernetes.resources.statefulsets.client.AppsV1Api")
    def test_iter_resources_pagination(self, mock_apps_v1_api):
        """Test pagination when listing statefulsets."""
        # Setup mock statefulsets for two pages
        mock_statefulset1 = MagicMock(spec=V1StatefulSet)
        mock_statefulset1.metadata.name = "test-statefulset-1"

        mock_statefulset2 = MagicMock(spec=V1StatefulSet)
        mock_statefulset2.metadata.name = "test-statefulset-2"

        # Configure mock api responses for pagination
        mock_result1 = MagicMock()
        mock_result1.items = [mock_statefulset1]
        mock_result1.metadata._continue = "continue-token"

        mock_result2 = MagicMock()
        mock_result2.items = [mock_statefulset2]
        mock_result2.metadata._continue = None

        # Configure the mock to return different results on subsequent calls
        self.mock_connection.apps_v1_api.list_namespaced_stateful_set.side_effect = [mock_result1, mock_result2]

        # Execute the method
        statefulsets = list(self.statefulset_resource.iter_resources())

        # Assertions
        self.assertEqual(len(statefulsets), 2)
        self.assertEqual(statefulsets[0].metadata.name, "test-statefulset-1")
        self.assertEqual(statefulsets[1].metadata.name, "test-statefulset-2")

        # Verify that the API was called twice with the appropriate continue token
        self.mock_connection.apps_v1_api.list_namespaced_stateful_set.assert_any_call(
            "default", limit=100, _continue=None
        )
        self.mock_connection.apps_v1_api.list_namespaced_stateful_set.assert_any_call(
            "default", limit=100, _continue="continue-token"
        )

    def test_get_resource(self):
        """Test getting a specific statefulset by name and namespace."""
        # Setup mock statefulset
        mock_statefulset = MagicMock(spec=V1StatefulSet)
        mock_statefulset.metadata.name = "test-statefulset"
        mock_statefulset.metadata.namespace = "default"

        # Configure mock api response
        self.mock_connection.apps_v1_api.read_namespaced_stateful_set.return_value = mock_statefulset

        # Execute the method
        statefulset = self.statefulset_resource.get_resource("test-statefulset", "default")

        # Assertions
        self.assertEqual(statefulset, mock_statefulset)
        self.mock_connection.apps_v1_api.read_namespaced_stateful_set.assert_called_once_with(
            "test-statefulset", "default"
        )

    def test_get_replicas(self):
        """Test getting the replica count from a statefulset."""
        # Setup mock statefulset with 3 replicas
        mock_statefulset = MagicMock(spec=V1StatefulSet)
        mock_statefulset.spec.replicas = 3

        # Execute the method
        replicas = self.statefulset_resource.get_replicas(mock_statefulset)

        # Assertions
        self.assertEqual(replicas, 3)

    def test_get_replicas_none(self):
        """Test getting replicas when the value is None."""
        # Setup mock statefulset with None replicas
        mock_statefulset = MagicMock(spec=V1StatefulSet)
        mock_statefulset.spec.replicas = None

        # Execute the method
        replicas = self.statefulset_resource.get_replicas(mock_statefulset)

        # Assertions
        self.assertEqual(replicas, 0)

    def test_get_current_state(self):
        """Test getting the current state of a statefulset."""
        # Setup mock statefulset
        mock_statefulset = MagicMock(spec=V1StatefulSet)
        mock_statefulset.spec.replicas = 5

        # Execute the method
        state = self.statefulset_resource.get_current_state(mock_statefulset)

        # Assertions
        self.assertEqual(state, 5)

    def test_is_suspended_true(self):
        """Test checking if a statefulset is suspended (0 replicas)."""
        # Setup mock statefulset with 0 replicas
        mock_statefulset = MagicMock(spec=V1StatefulSet)
        mock_statefulset.spec.replicas = 0

        # Execute the method
        is_suspended = self.statefulset_resource.is_suspended(mock_statefulset)

        # Assertions
        self.assertTrue(is_suspended)

    def test_is_suspended_false(self):
        """Test checking if a statefulset is not suspended (> 0 replicas)."""
        # Setup mock statefulset with > 0 replicas
        mock_statefulset = MagicMock(spec=V1StatefulSet)
        mock_statefulset.spec.replicas = 1

        # Execute the method
        is_suspended = self.statefulset_resource.is_suspended(mock_statefulset)

        # Assertions
        self.assertFalse(is_suspended)

    def test_set_replicas(self):
        """Test setting replicas for a statefulset."""
        # Setup mock statefulset
        mock_statefulset = MagicMock(spec=V1StatefulSet)
        mock_statefulset.metadata.name = "test-statefulset"
        mock_statefulset.metadata.namespace = "default"

        # Execute the method
        self.statefulset_resource.set_replicas(mock_statefulset, 3)

        # Assertions
        self.mock_connection.apps_v1_api.patch_namespaced_stateful_set.assert_called_once_with(
            name="test-statefulset", namespace="default", body={"spec": {"replicas": 3}}
        )

    def test_suspend_resource(self):
        """Test suspending a statefulset by setting replicas to 0."""
        # Setup mock statefulset
        mock_statefulset = MagicMock(spec=V1StatefulSet)

        # Create a spy for set_replicas
        with patch.object(self.statefulset_resource, "set_replicas") as mock_set_replicas:
            # Execute the method
            self.statefulset_resource.suspend_resource(mock_statefulset)

            # Assertions
            mock_set_replicas.assert_called_once_with(mock_statefulset, 0)

    def test_resume_resource(self):
        """Test resuming a statefulset by restoring replicas."""
        # Setup mock statefulset
        mock_statefulset = MagicMock(spec=V1StatefulSet)

        # Create a spy for set_replicas
        with patch.object(self.statefulset_resource, "set_replicas") as mock_set_replicas:
            # Execute the method
            self.statefulset_resource.resume_resource(mock_statefulset, 5)

            # Assertions
            mock_set_replicas.assert_called_once_with(mock_statefulset, 5)

    def test_get_resource_key(self):
        """Test getting a unique key for a statefulset."""
        # Setup mock statefulset
        mock_statefulset = MagicMock(spec=V1StatefulSet)
        mock_statefulset.metadata.namespace = "default"
        mock_statefulset.metadata.name = "test-statefulset"

        # Execute the method
        key = self.statefulset_resource.get_resource_key(mock_statefulset)

        # Assertions
        self.assertEqual(key, "default/test-statefulset")

    def test_get_resource_name(self):
        """Test getting the name of a statefulset."""
        # Setup mock statefulset
        mock_statefulset = MagicMock(spec=V1StatefulSet)
        mock_statefulset.metadata.name = "test-statefulset"

        # Execute the method
        name = self.statefulset_resource.get_resource_name(mock_statefulset)

        # Assertions
        self.assertEqual(name, "test-statefulset")

    def test_get_resource_namespace(self):
        """Test getting the namespace of a statefulset."""
        # Setup mock statefulset
        mock_statefulset = MagicMock(spec=V1StatefulSet)
        mock_statefulset.metadata.namespace = "default"

        # Execute the method
        namespace = self.statefulset_resource.get_resource_namespace(mock_statefulset)

        # Assertions
        self.assertEqual(namespace, "default")

    def test_save_annotation(self):
        """Test saving an annotation on a statefulset."""
        # Setup mock statefulset
        mock_statefulset = MagicMock(spec=V1StatefulSet)
        mock_statefulset.metadata.name = "test-statefulset"
        mock_statefulset.metadata.namespace = "default"

        # Execute the method
        self.statefulset_resource._save_annotation(mock_statefulset, "test-key", "test-value")

        # Assertions
        self.mock_connection.apps_v1_api.patch_namespaced_stateful_set.assert_called_once_with(
            name="test-statefulset", namespace="default", body={"metadata": {"annotations": {"test-key": "test-value"}}}
        )

    def test_get_annotation_exists(self):
        """Test getting an existing annotation from a statefulset."""
        # Setup mock statefulset with annotations
        mock_statefulset = MagicMock(spec=V1StatefulSet)
        mock_statefulset.metadata.annotations = {"test-key": "test-value"}

        # Execute the method
        value = self.statefulset_resource._get_annotation(mock_statefulset, "test-key")

        # Assertions
        self.assertEqual(value, "test-value")

    def test_get_annotation_not_exists(self):
        """Test getting a non-existent annotation from a statefulset."""
        # Setup mock statefulset with no annotations
        mock_statefulset = MagicMock(spec=V1StatefulSet)
        mock_statefulset.metadata.annotations = {}

        # Execute the method
        value = self.statefulset_resource._get_annotation(mock_statefulset, "non-existent-key")

        # Assertions
        self.assertIsNone(value)

    def test_get_annotation_no_annotations(self):
        """Test getting an annotation when annotations attribute is None."""
        # Setup mock statefulset with no annotations attribute
        mock_statefulset = MagicMock(spec=V1StatefulSet)
        mock_statefulset.metadata.annotations = None

        # Execute the method
        value = self.statefulset_resource._get_annotation(mock_statefulset, "test-key")

        # Assertions
        self.assertIsNone(value)


if __name__ == "__main__":
    unittest.main()
