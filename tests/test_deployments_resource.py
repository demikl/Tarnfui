import unittest
from unittest.mock import MagicMock, patch

from kubernetes.client import V1Deployment

from tarnfui.kubernetes.connection import KubernetesConnection
from tarnfui.kubernetes.resources.deployments import DeploymentResource


class TestDeploymentResource(unittest.TestCase):
    """Unit tests for the DeploymentResource class."""

    def setUp(self):
        """Set up test environment before each test method."""
        # Create a mock KubernetesConnection with the necessary attributes
        self.mock_connection = MagicMock(spec=KubernetesConnection)
        self.mock_connection.apps_v1_api = MagicMock()
        self.deployment_resource = DeploymentResource(self.mock_connection, namespace="default")

    @patch("tarnfui.kubernetes.resources.deployments.client.AppsV1Api")
    def test_iter_resources_with_namespace(self, mock_apps_v1_api):
        """Test listing deployments in a specific namespace."""
        # Setup mock deployment
        mock_deployment = MagicMock(spec=V1Deployment)
        mock_deployment.metadata.name = "test-deployment"
        mock_deployment.metadata.namespace = "default"

        # Configure mock api response
        mock_result = MagicMock()
        mock_result.items = [mock_deployment]
        mock_result.metadata._continue = None
        self.mock_connection.apps_v1_api.list_namespaced_deployment.return_value = mock_result

        # Execute the method
        deployments = list(self.deployment_resource.iter_resources())

        # Assertions
        self.assertEqual(len(deployments), 1)
        self.assertEqual(deployments[0].metadata.name, "test-deployment")
        self.mock_connection.apps_v1_api.list_namespaced_deployment.assert_called_once_with(
            "default", limit=100, _continue=None
        )

    @patch("tarnfui.kubernetes.resources.deployments.client.AppsV1Api")
    def test_iter_resources_all_namespaces(self, mock_apps_v1_api):
        """Test listing deployments across all namespaces."""
        # Setup mock deployment
        mock_deployment = MagicMock(spec=V1Deployment)
        mock_deployment.metadata.name = "test-deployment"
        mock_deployment.metadata.namespace = "default"

        # Configure mock api response
        mock_result = MagicMock()
        mock_result.items = [mock_deployment]
        mock_result.metadata._continue = None
        self.mock_connection.apps_v1_api.list_deployment_for_all_namespaces.return_value = mock_result

        # Create a resource handler without namespace filter
        all_ns_resource = DeploymentResource(self.mock_connection, namespace=None)

        # Execute the method
        deployments = list(all_ns_resource.iter_resources())

        # Assertions
        self.assertEqual(len(deployments), 1)
        self.assertEqual(deployments[0].metadata.name, "test-deployment")
        self.mock_connection.apps_v1_api.list_deployment_for_all_namespaces.assert_called_once_with(
            limit=100, _continue=None
        )

    @patch("tarnfui.kubernetes.resources.deployments.client.AppsV1Api")
    def test_iter_resources_pagination(self, mock_apps_v1_api):
        """Test pagination when listing deployments."""
        # Setup mock deployments for two pages
        mock_deployment1 = MagicMock(spec=V1Deployment)
        mock_deployment1.metadata.name = "test-deployment-1"

        mock_deployment2 = MagicMock(spec=V1Deployment)
        mock_deployment2.metadata.name = "test-deployment-2"

        # Configure mock api responses for pagination
        mock_result1 = MagicMock()
        mock_result1.items = [mock_deployment1]
        mock_result1.metadata._continue = "continue-token"

        mock_result2 = MagicMock()
        mock_result2.items = [mock_deployment2]
        mock_result2.metadata._continue = None

        # Configure the mock to return different results on subsequent calls
        self.mock_connection.apps_v1_api.list_namespaced_deployment.side_effect = [mock_result1, mock_result2]

        # Execute the method
        deployments = list(self.deployment_resource.iter_resources())

        # Assertions
        self.assertEqual(len(deployments), 2)
        self.assertEqual(deployments[0].metadata.name, "test-deployment-1")
        self.assertEqual(deployments[1].metadata.name, "test-deployment-2")

        # Verify that the API was called twice with the appropriate continue token
        self.mock_connection.apps_v1_api.list_namespaced_deployment.assert_any_call(
            "default", limit=100, _continue=None
        )
        self.mock_connection.apps_v1_api.list_namespaced_deployment.assert_any_call(
            "default", limit=100, _continue="continue-token"
        )

    def test_get_resource(self):
        """Test getting a specific deployment by name and namespace."""
        # Setup mock deployment
        mock_deployment = MagicMock(spec=V1Deployment)
        mock_deployment.metadata.name = "test-deployment"
        mock_deployment.metadata.namespace = "default"

        # Configure mock api response
        self.mock_connection.apps_v1_api.read_namespaced_deployment.return_value = mock_deployment

        # Execute the method
        deployment = self.deployment_resource.get_resource("test-deployment", "default")

        # Assertions
        self.assertEqual(deployment, mock_deployment)
        self.mock_connection.apps_v1_api.read_namespaced_deployment.assert_called_once_with(
            "test-deployment", "default"
        )

    def test_get_replicas(self):
        """Test getting the replica count from a deployment."""
        # Setup mock deployment with 3 replicas
        mock_deployment = MagicMock(spec=V1Deployment)
        mock_deployment.spec.replicas = 3

        # Execute the method
        replicas = self.deployment_resource.get_replicas(mock_deployment)

        # Assertions
        self.assertEqual(replicas, 3)

    def test_get_replicas_none(self):
        """Test getting replicas when the value is None."""
        # Setup mock deployment with None replicas
        mock_deployment = MagicMock(spec=V1Deployment)
        mock_deployment.spec.replicas = None

        # Execute the method
        replicas = self.deployment_resource.get_replicas(mock_deployment)

        # Assertions
        self.assertEqual(replicas, 0)

    def test_get_current_state(self):
        """Test getting the current state of a deployment."""
        # Setup mock deployment
        mock_deployment = MagicMock(spec=V1Deployment)
        mock_deployment.spec.replicas = 5

        # Execute the method
        state = self.deployment_resource.get_current_state(mock_deployment)

        # Assertions
        self.assertEqual(state, 5)

    def test_is_suspended_true(self):
        """Test checking if a deployment is suspended (0 replicas)."""
        # Setup mock deployment with 0 replicas
        mock_deployment = MagicMock(spec=V1Deployment)
        mock_deployment.spec.replicas = 0

        # Execute the method
        is_suspended = self.deployment_resource.is_suspended(mock_deployment)

        # Assertions
        self.assertTrue(is_suspended)

    def test_is_suspended_false(self):
        """Test checking if a deployment is not suspended (> 0 replicas)."""
        # Setup mock deployment with > 0 replicas
        mock_deployment = MagicMock(spec=V1Deployment)
        mock_deployment.spec.replicas = 1

        # Execute the method
        is_suspended = self.deployment_resource.is_suspended(mock_deployment)

        # Assertions
        self.assertFalse(is_suspended)

    def test_set_replicas(self):
        """Test setting replicas for a deployment."""
        # Setup mock deployment
        mock_deployment = MagicMock(spec=V1Deployment)
        mock_deployment.metadata.name = "test-deployment"
        mock_deployment.metadata.namespace = "default"

        # Execute the method
        self.deployment_resource.set_replicas(mock_deployment, 3)

        # Assertions
        self.mock_connection.apps_v1_api.patch_namespaced_deployment.assert_called_once_with(
            name="test-deployment", namespace="default", body={"spec": {"replicas": 3}}
        )

    def test_suspend_resource(self):
        """Test suspending a deployment by setting replicas to 0."""
        # Setup mock deployment
        mock_deployment = MagicMock(spec=V1Deployment)

        # Create a spy for set_replicas
        with patch.object(self.deployment_resource, "set_replicas") as mock_set_replicas:
            # Execute the method
            self.deployment_resource.suspend_resource(mock_deployment)

            # Assertions
            mock_set_replicas.assert_called_once_with(mock_deployment, 0)

    def test_resume_resource(self):
        """Test resuming a deployment by restoring replicas."""
        # Setup mock deployment
        mock_deployment = MagicMock(spec=V1Deployment)

        # Create a spy for set_replicas
        with patch.object(self.deployment_resource, "set_replicas") as mock_set_replicas:
            # Execute the method
            self.deployment_resource.resume_resource(mock_deployment, 5)

            # Assertions
            mock_set_replicas.assert_called_once_with(mock_deployment, 5)

    def test_get_resource_key(self):
        """Test getting a unique key for a deployment."""
        # Setup mock deployment
        mock_deployment = MagicMock(spec=V1Deployment)
        mock_deployment.metadata.namespace = "default"
        mock_deployment.metadata.name = "test-deployment"

        # Execute the method
        key = self.deployment_resource.get_resource_key(mock_deployment)

        # Assertions
        self.assertEqual(key, "default/test-deployment")

    def test_get_resource_name(self):
        """Test getting the name of a deployment."""
        # Setup mock deployment
        mock_deployment = MagicMock(spec=V1Deployment)
        mock_deployment.metadata.name = "test-deployment"

        # Execute the method
        name = self.deployment_resource.get_resource_name(mock_deployment)

        # Assertions
        self.assertEqual(name, "test-deployment")

    def test_get_resource_namespace(self):
        """Test getting the namespace of a deployment."""
        # Setup mock deployment
        mock_deployment = MagicMock(spec=V1Deployment)
        mock_deployment.metadata.namespace = "default"

        # Execute the method
        namespace = self.deployment_resource.get_resource_namespace(mock_deployment)

        # Assertions
        self.assertEqual(namespace, "default")

    def test_save_annotation(self):
        """Test saving an annotation on a deployment."""
        # Setup mock deployment
        mock_deployment = MagicMock(spec=V1Deployment)
        mock_deployment.metadata.name = "test-deployment"
        mock_deployment.metadata.namespace = "default"

        # Execute the method
        self.deployment_resource._save_annotation(mock_deployment, "test-key", "test-value")

        # Assertions
        self.mock_connection.apps_v1_api.patch_namespaced_deployment.assert_called_once_with(
            name="test-deployment", namespace="default", body={"metadata": {"annotations": {"test-key": "test-value"}}}
        )

    def test_get_annotation_exists(self):
        """Test getting an existing annotation from a deployment."""
        # Setup mock deployment with annotations
        mock_deployment = MagicMock(spec=V1Deployment)
        mock_deployment.metadata.annotations = {"test-key": "test-value"}

        # Execute the method
        value = self.deployment_resource._get_annotation(mock_deployment, "test-key")

        # Assertions
        self.assertEqual(value, "test-value")

    def test_get_annotation_not_exists(self):
        """Test getting a non-existent annotation from a deployment."""
        # Setup mock deployment with no annotations
        mock_deployment = MagicMock(spec=V1Deployment)
        mock_deployment.metadata.annotations = {}

        # Execute the method
        value = self.deployment_resource._get_annotation(mock_deployment, "non-existent-key")

        # Assertions
        self.assertIsNone(value)

    def test_get_annotation_no_annotations(self):
        """Test getting an annotation when annotations attribute is None."""
        # Setup mock deployment with no annotations attribute
        mock_deployment = MagicMock(spec=V1Deployment)
        mock_deployment.metadata.annotations = None

        # Execute the method
        value = self.deployment_resource._get_annotation(mock_deployment, "test-key")

        # Assertions
        self.assertIsNone(value)


if __name__ == "__main__":
    unittest.main()
