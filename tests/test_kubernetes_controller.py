"""Tests for the Kubernetes controller module."""

import unittest
from unittest import mock

from tarnfui.kubernetes.base import KubernetesResource
from tarnfui.kubernetes.connection import KubernetesConnection
from tarnfui.kubernetes.controller import KubernetesController
from tarnfui.kubernetes.resources.deployments import DeploymentResource
from tarnfui.kubernetes.resources.statefulsets import StatefulSetResource


class TestKubernetesController(unittest.TestCase):
    """Test cases for the KubernetesController class."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock the KubernetesConnection
        self.connection_mock = mock.Mock(spec=KubernetesConnection)
        # Add the apps_v1_api attribute to the connection mock
        self.connection_mock.apps_v1_api = mock.Mock()

        # Patch the KubernetesConnection constructor
        self.connection_patcher = mock.patch("tarnfui.kubernetes.controller.KubernetesConnection")
        self.connection_class_mock = self.connection_patcher.start()
        self.connection_class_mock.return_value = self.connection_mock

        # Patch the DeploymentResource class
        self.deployment_resource_patcher = mock.patch("tarnfui.kubernetes.controller.DeploymentResource")
        self.deployment_resource_class_mock = self.deployment_resource_patcher.start()
        self.deployment_resource_mock = mock.Mock(spec=DeploymentResource)
        self.deployment_resource_class_mock.return_value = self.deployment_resource_mock

        # Patch the StatefulSetResource class
        self.statefulset_resource_patcher = mock.patch("tarnfui.kubernetes.controller.StatefulSetResource")
        self.statefulset_resource_class_mock = self.statefulset_resource_patcher.start()
        self.statefulset_resource_mock = mock.Mock(spec=StatefulSetResource)
        self.statefulset_resource_class_mock.return_value = self.statefulset_resource_mock

        # Create the controller instance
        self.namespace = "test-namespace"
        self.controller = KubernetesController(namespace=self.namespace)

    def tearDown(self):
        """Tear down test fixtures."""
        self.connection_patcher.stop()
        self.deployment_resource_patcher.stop()
        self.statefulset_resource_patcher.stop()

    def test_init_with_namespace(self):
        """Test that the controller is initialized with a namespace."""
        self.assertEqual(self.controller.namespace, self.namespace)
        self.connection_class_mock.assert_called_once()
        self.deployment_resource_class_mock.assert_called_once_with(self.connection_mock, self.namespace)
        self.statefulset_resource_class_mock.assert_called_once_with(self.connection_mock, self.namespace)

    def test_init_without_namespace(self):
        """Test that the controller is initialized without a namespace."""
        controller = KubernetesController()
        self.assertIsNone(controller.namespace)

    def test_register_resource(self):
        """Test registering a resource handler."""
        # Create a mock resource handler
        resource_handler = mock.Mock(spec=KubernetesResource)
        resource_type = "test-resource"

        # Register the resource
        self.controller.register_resource(resource_type, resource_handler)

        # Verify that the resource was registered
        self.assertIn(resource_type, self.controller.resources)
        self.assertEqual(self.controller.resources[resource_type], resource_handler)

    def test_get_handler_existing(self):
        """Test getting an existing resource handler."""
        # Create and register a mock resource handler
        resource_handler = mock.Mock(spec=KubernetesResource)
        resource_type = "test-resource"
        self.controller.resources[resource_type] = resource_handler

        # Get the handler
        handler = self.controller.get_handler(resource_type)

        # Verify that the correct handler was returned
        self.assertEqual(handler, resource_handler)

    def test_get_handler_nonexistent(self):
        """Test getting a non-existent resource handler."""
        # Get a non-existent handler
        handler = self.controller.get_handler("non-existent")

        # Verify that None was returned
        self.assertIsNone(handler)

    def test_suspend_resources_specific_types(self):
        """Test suspending specific resource types."""
        # Create and register mock resource handlers
        deployment_handler = mock.Mock(spec=KubernetesResource)
        statefulset_handler = mock.Mock(spec=KubernetesResource)
        self.controller.resources["deployments"] = deployment_handler
        self.controller.resources["statefulsets"] = statefulset_handler

        # Suspend only deployments
        resource_types = ["deployments"]
        self.controller.suspend_resources(resource_types, self.namespace)

        # Verify that only the deployment handler was called
        deployment_handler.stop_resources.assert_called_once_with(namespace=self.namespace)
        statefulset_handler.stop_resources.assert_not_called()

    def test_suspend_resources_all_types(self):
        """Test suspending all resource types."""
        # Create and register mock resource handlers
        deployment_handler = mock.Mock(spec=KubernetesResource)
        statefulset_handler = mock.Mock(spec=KubernetesResource)
        self.controller.resources["deployments"] = deployment_handler
        self.controller.resources["statefulsets"] = statefulset_handler

        # Suspend all resources
        self.controller.suspend_resources(None, self.namespace)

        # Verify that both handlers were called
        deployment_handler.stop_resources.assert_called_once_with(namespace=self.namespace)
        statefulset_handler.stop_resources.assert_called_once_with(namespace=self.namespace)

    def test_resume_resources_specific_types(self):
        """Test resuming specific resource types."""
        # Create and register mock resource handlers
        deployment_handler = mock.Mock(spec=KubernetesResource)
        statefulset_handler = mock.Mock(spec=KubernetesResource)
        self.controller.resources["deployments"] = deployment_handler
        self.controller.resources["statefulsets"] = statefulset_handler

        # Resume only deployments
        resource_types = ["deployments"]
        self.controller.resume_resources(resource_types, self.namespace)

        # Verify that only the deployment handler was called
        deployment_handler.start_resources.assert_called_once_with(namespace=self.namespace)
        statefulset_handler.start_resources.assert_not_called()

    def test_resume_resources_all_types(self):
        """Test resuming all resource types."""
        # Create and register mock resource handlers
        deployment_handler = mock.Mock(spec=KubernetesResource)
        statefulset_handler = mock.Mock(spec=KubernetesResource)
        self.controller.resources["deployments"] = deployment_handler
        self.controller.resources["statefulsets"] = statefulset_handler

        # Resume all resources
        self.controller.resume_resources(None, self.namespace)

        # Verify that both handlers were called
        deployment_handler.start_resources.assert_called_once_with(namespace=self.namespace)
        statefulset_handler.start_resources.assert_called_once_with(namespace=self.namespace)

    def test_get_resource_state(self):
        """Test getting the current state of a resource."""
        # Create and register a mock resource handler
        resource_handler = mock.Mock(spec=KubernetesResource)
        resource_type = "test-resource"
        self.controller.resources[resource_type] = resource_handler

        # Setup mock return values
        resource_name = "test-resource-name"
        resource_namespace = "test-resource-namespace"
        resource_mock = mock.Mock()
        resource_handler.get_resource.return_value = resource_mock
        expected_state = 3  # Example state value
        resource_handler.get_current_state.return_value = expected_state

        # Get the resource state
        state = self.controller.get_resource_state(resource_type, resource_name, resource_namespace)

        # Verify that the methods were called correctly
        resource_handler.get_resource.assert_called_once_with(resource_name, resource_namespace)
        resource_handler.get_current_state.assert_called_once_with(resource_mock)
        self.assertEqual(state, expected_state)

    def test_get_resource_state_nonexistent_type(self):
        """Test getting the state of a non-existent resource type."""
        # Get the state of a non-existent resource type
        state = self.controller.get_resource_state("non-existent", "name", "namespace")

        # Verify that None was returned
        self.assertIsNone(state)

    def test_get_resource_state_with_exception(self):
        """Test getting the state of a resource when an exception occurs."""
        # Create and register a mock resource handler
        resource_handler = mock.Mock(spec=KubernetesResource)
        resource_type = "test-resource"
        self.controller.resources[resource_type] = resource_handler

        # Setup the mock to raise an exception
        resource_handler.get_resource.side_effect = Exception("Test exception")

        # Get the resource state
        state = self.controller.get_resource_state(resource_type, "name", "namespace")

        # Verify that None was returned
        self.assertIsNone(state)

    def test_get_saved_state(self):
        """Test getting the saved state of a resource."""
        # Create and register a mock resource handler
        resource_handler = mock.Mock(spec=KubernetesResource)
        resource_type = "test-resource"
        self.controller.resources[resource_type] = resource_handler

        # Setup mock return values
        resource_name = "test-resource-name"
        resource_namespace = "test-resource-namespace"
        resource_mock = mock.Mock()
        resource_handler.get_resource.return_value = resource_mock
        expected_state = 3  # Example state value
        resource_handler.get_saved_state.return_value = expected_state

        # Get the saved state
        state = self.controller.get_saved_state(resource_type, resource_name, resource_namespace)

        # Verify that the methods were called correctly
        resource_handler.get_resource.assert_called_once_with(resource_name, resource_namespace)
        resource_handler.get_saved_state.assert_called_once_with(resource_mock)
        self.assertEqual(state, expected_state)

    def test_get_saved_state_nonexistent_type(self):
        """Test getting the saved state of a non-existent resource type."""
        # Get the saved state of a non-existent resource type
        state = self.controller.get_saved_state("non-existent", "name", "namespace")

        # Verify that None was returned
        self.assertIsNone(state)

    def test_get_saved_state_with_exception(self):
        """Test getting the saved state of a resource when an exception occurs."""
        # Create and register a mock resource handler
        resource_handler = mock.Mock(spec=KubernetesResource)
        resource_type = "test-resource"
        self.controller.resources[resource_type] = resource_handler

        # Setup the mock to raise an exception
        resource_handler.get_resource.side_effect = Exception("Test exception")

        # Get the saved state
        state = self.controller.get_saved_state(resource_type, "name", "namespace")

        # Verify that None was returned
        self.assertIsNone(state)


if __name__ == "__main__":
    unittest.main()
