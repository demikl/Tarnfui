"""Tests for the kubernetes client module."""

import unittest
from unittest import mock

from kubernetes import client
from kubernetes.client.models.v1_deployment import V1Deployment
from kubernetes.client.models.v1_deployment_spec import V1DeploymentSpec
from kubernetes.client.models.v1_object_meta import V1ObjectMeta

from tarnfui.kubernetes import KubernetesClient


class TestKubernetesClient(unittest.TestCase):
    """Test cases for the KubernetesClient class."""

    @mock.patch('kubernetes.config.load_incluster_config')
    @mock.patch('kubernetes.config.load_kube_config')
    def setUp(self, mock_load_kube_config, mock_load_incluster_config):
        """Set up test fixtures."""
        # Setup to use kubeconfig for tests
        mock_load_incluster_config.side_effect = client.config.ConfigException()

        self.k8s_client = KubernetesClient()
        self.k8s_client.api = mock.Mock(spec=client.AppsV1Api)

        # Create test deployments
        self.test_deployments = [
            self._create_test_deployment("deployment1", "default", 3),
            self._create_test_deployment("deployment2", "default", 2),
            self._create_test_deployment("deployment3", "kube-system", 1)
        ]

    def _create_test_deployment(self, name, namespace, replicas):
        """Helper method to create test deployment objects."""
        deployment = mock.Mock(spec=V1Deployment)
        deployment.metadata = V1ObjectMeta(name=name, namespace=namespace)
        deployment.spec = V1DeploymentSpec(replicas=replicas)
        return deployment

    def test_list_deployments_with_namespace(self):
        """Test listing deployments in a specific namespace."""
        namespace = "default"
        self.k8s_client.api.list_namespaced_deployment.return_value.items = [
            d for d in self.test_deployments if d.metadata.namespace == namespace
        ]

        deployments = self.k8s_client.list_deployments(namespace)

        self.assertEqual(len(deployments), 2)
        self.k8s_client.api.list_namespaced_deployment.assert_called_once_with(
            namespace)

    def test_list_deployments_all_namespaces(self):
        """Test listing deployments across all namespaces."""
        self.k8s_client.api.list_deployment_for_all_namespaces.return_value.items = self.test_deployments

        deployments = self.k8s_client.list_deployments()

        self.assertEqual(len(deployments), 3)
        self.k8s_client.api.list_deployment_for_all_namespaces.assert_called_once()

    def test_save_deployment_state(self):
        """Test saving the state of a deployment."""
        deployment = self.test_deployments[0]

        self.k8s_client.save_deployment_state(deployment)

        key = f"{deployment.metadata.namespace}/{deployment.metadata.name}"
        self.assertIn(key, self.k8s_client.deployment_replicas)
        self.assertEqual(
            self.k8s_client.deployment_replicas[key], deployment.spec.replicas)

    def test_scale_deployment(self):
        """Test scaling a deployment to a specific number of replicas."""
        deployment = self.test_deployments[0]
        new_replicas = 0

        self.k8s_client.scale_deployment(deployment, new_replicas)

        key = f"{deployment.metadata.namespace}/{deployment.metadata.name}"
        self.assertIn(key, self.k8s_client.deployment_replicas)
        self.assertEqual(
            self.k8s_client.deployment_replicas[key], deployment.spec.replicas)

        self.k8s_client.api.patch_namespaced_deployment.assert_called_once_with(
            name=deployment.metadata.name,
            namespace=deployment.metadata.namespace,
            body={"spec": {"replicas": new_replicas}}
        )

    def test_stop_deployments(self):
        """Test stopping all deployments in a namespace."""
        namespace = "default"
        self.k8s_client.api.list_namespaced_deployment.return_value.items = [
            d for d in self.test_deployments if d.metadata.namespace == namespace
        ]

        self.k8s_client.stop_deployments(namespace)

        # Verify that each deployment was scaled to 0
        for deployment in [d for d in self.test_deployments if d.metadata.namespace == namespace]:
            self.k8s_client.api.patch_namespaced_deployment.assert_any_call(
                name=deployment.metadata.name,
                namespace=deployment.metadata.namespace,
                body={"spec": {"replicas": 0}}
            )

    def test_start_deployments(self):
        """Test starting deployments with their saved replica counts."""
        namespace = "default"
        self.k8s_client.api.list_namespaced_deployment.return_value.items = [
            self._create_test_deployment("deployment1", "default", 0),
            self._create_test_deployment("deployment2", "default", 0)
        ]

        # Pre-populate the saved states
        self.k8s_client.deployment_replicas = {
            "default/deployment1": 3,
            "default/deployment2": 2
        }

        self.k8s_client.start_deployments(namespace)

        # Verify that deployments were restored to their original replica counts
        self.k8s_client.api.patch_namespaced_deployment.assert_any_call(
            name="deployment1",
            namespace="default",
            body={"spec": {"replicas": 3}}
        )
        self.k8s_client.api.patch_namespaced_deployment.assert_any_call(
            name="deployment2",
            namespace="default",
            body={"spec": {"replicas": 2}}
        )


if __name__ == "__main__":
    unittest.main()
