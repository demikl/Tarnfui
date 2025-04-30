"""Tests for the Kustomization resource manager."""

import unittest
from unittest.mock import MagicMock, patch

from kubernetes.client.models.v1_deployment import V1Deployment
from kubernetes.client.models.v1_object_meta import V1ObjectMeta

from tarnfui.kubernetes.connection import KubernetesConnection
from tarnfui.kubernetes.resources.managers import Kustomization


class TestKustomization(unittest.TestCase):
    """Unit tests for the Kustomization class."""

    def setUp(self):
        """Set up test environment before each test method."""
        # Create a mock KubernetesConnection
        self.mock_connection = MagicMock(spec=KubernetesConnection)
        self.mock_connection.custom_objects_api = MagicMock()

        # Create a Kustomization instance
        self.kustomization = Kustomization(self.mock_connection, namespace="default")

        # Create a mock kustomization resource
        self.mock_kustomization = {
            "metadata": {
                "name": "test-kustomization",
                "namespace": "default",
                "annotations": {}
            },
            "spec": {
                "suspend": False,
                "interval": "10m",
                "path": "./kustomize",
                "prune": True
            }
        }

        # Create a mock deployment resource managed by a Kustomization
        self.mock_deployment = MagicMock(spec=V1Deployment)
        self.mock_deployment.metadata = MagicMock(spec=V1ObjectMeta)
        self.mock_deployment.metadata.name = "test-deployment"
        self.mock_deployment.metadata.namespace = "default"
        self.mock_deployment.metadata.labels = {
            "kustomize.toolkit.fluxcd.io/name": "test-kustomization",
            "app.kubernetes.io/instance": "test-app"
        }

        # Create a mock deployment with only app.kubernetes.io/managed-by label
        self.mock_managed_deployment = MagicMock(spec=V1Deployment)
        self.mock_managed_deployment.metadata = MagicMock(spec=V1ObjectMeta)
        self.mock_managed_deployment.metadata.name = "managed-deployment"
        self.mock_managed_deployment.metadata.namespace = "default"
        self.mock_managed_deployment.metadata.labels = {
            "app.kubernetes.io/managed-by": "kustomize-controller",
            "app.kubernetes.io/instance": "test-app"
        }

    def test_get_current_state(self):
        """Test getting the current state of a Kustomization."""
        # Test with suspend=False
        state = self.kustomization.get_current_state(self.mock_kustomization)
        self.assertFalse(state)

        # Test with suspend=True
        self.mock_kustomization["spec"]["suspend"] = True
        state = self.kustomization.get_current_state(self.mock_kustomization)
        self.assertTrue(state)

    def test_suspend_resource(self):
        """Test suspending a Kustomization."""
        # Setup patch_resource mock
        self.kustomization.patch_resource = MagicMock()

        # Suspend the resource
        self.kustomization.suspend_resource(self.mock_kustomization)

        # Verify patch_resource was called with correct arguments
        self.kustomization.patch_resource.assert_called_once_with(
            self.mock_kustomization,
            {"spec": {"suspend": True}}
        )

    def test_resume_resource(self):
        """Test resuming a Kustomization."""
        # Setup patch_resource mock
        self.kustomization.patch_resource = MagicMock()

        # Resume the resource with saved_state=False
        self.kustomization.resume_resource(self.mock_kustomization, False)

        # Verify patch_resource was called with correct arguments
        self.kustomization.patch_resource.assert_called_once_with(
            self.mock_kustomization,
            {"spec": {"suspend": False}}
        )

        # Reset the mock
        self.kustomization.patch_resource.reset_mock()

        # Resume the resource with saved_state=True
        self.kustomization.resume_resource(self.mock_kustomization, True)

        # Verify patch_resource was called with correct arguments
        self.kustomization.patch_resource.assert_called_once_with(
            self.mock_kustomization,
            {"spec": {"suspend": True}}
        )

    def test_is_suspended(self):
        """Test checking if a Kustomization is suspended."""
        # Test with suspend=False
        self.mock_kustomization["spec"]["suspend"] = False
        is_suspended = self.kustomization.is_suspended(self.mock_kustomization)
        self.assertFalse(is_suspended)

        # Test with suspend=True
        self.mock_kustomization["spec"]["suspend"] = True
        is_suspended = self.kustomization.is_suspended(self.mock_kustomization)
        self.assertTrue(is_suspended)

    def test_find_manager_for_resource_with_kustomize_name_label(self):
        """Test finding a manager for a resource with the kustomize.toolkit.fluxcd.io/name label."""
        # Setup get_resource mock to return a Kustomization
        with patch.object(Kustomization, 'get_resource') as mock_get_resource:
            mock_get_resource.return_value = self.mock_kustomization

            # Test finding a manager
            manager = Kustomization.find_manager_for_resource(
                self.mock_deployment, self.mock_connection
            )

            # Verify a manager was found
            self.assertIsNotNone(manager)
            self.assertIsInstance(manager, Kustomization)

            # Verify get_resource was called with correct arguments
            mock_get_resource.assert_called_once_with("test-kustomization", "default")

    def test_find_manager_for_resource_with_managed_by_label(self):
        """Test finding a manager for a resource with only the app.kubernetes.io/managed-by label."""
        # Test finding a manager with only the managed-by label
        manager = Kustomization.find_manager_for_resource(
            self.mock_managed_deployment, self.mock_connection
        )

        # Verify no manager was found (since we need the specific kustomization name)
        self.assertIsNone(manager)

    def test_find_manager_for_resource_no_labels(self):
        """Test finding a manager for a resource with no relevant labels."""
        # Create a deployment with no relevant labels
        deployment = MagicMock(spec=V1Deployment)
        deployment.metadata = MagicMock(spec=V1ObjectMeta)
        deployment.metadata.name = "no-labels-deployment"
        deployment.metadata.namespace = "default"
        deployment.metadata.labels = {
            "app": "test-app"
        }

        # Test finding a manager
        manager = Kustomization.find_manager_for_resource(
            deployment, self.mock_connection
        )

        # Verify no manager was found
        self.assertIsNone(manager)

    def test_patch_resource(self):
        """Test patching a Kustomization resource."""
        # Call patch_resource
        self.kustomization.patch_resource(
            self.mock_kustomization,
            {"spec": {"suspend": True}}
        )

        # Verify custom_objects_api.patch_namespaced_custom_object was called correctly
        self.mock_connection.custom_objects_api.patch_namespaced_custom_object.assert_called_once_with(
            group="kustomize.toolkit.fluxcd.io",
            version="v1",
            namespace="default",
            plural="kustomizations",
            name="test-kustomization",
            body={"spec": {"suspend": True}}
        )


if __name__ == "__main__":
    unittest.main()
