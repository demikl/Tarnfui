"""Tests for the kubernetes client module."""

import unittest
from unittest import mock

from kubernetes import client
from kubernetes.client.models.v1_deployment import V1Deployment
from kubernetes.client.models.v1_deployment_spec import V1DeploymentSpec
from kubernetes.client.models.v1_object_meta import V1ObjectMeta

from tarnfui.kubernetes import TARNFUI_REPLICAS_ANNOTATION, KubernetesClient


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

    def _create_test_deployment(self, name, namespace, replicas, annotations=None):
        """Helper method to create test deployment objects.

        Args:
            name: Deployment name
            namespace: Deployment namespace
            replicas: Number of replicas
            annotations: Optional dict of annotations

        Returns:
            Mock deployment object
        """
        deployment = mock.Mock(spec=V1Deployment)
        deployment.metadata = V1ObjectMeta(
            name=name, namespace=namespace, annotations=annotations)
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

        # Check memory cache
        key = f"{deployment.metadata.namespace}/{deployment.metadata.name}"
        self.assertIn(key, self.k8s_client.deployment_replicas)
        self.assertEqual(
            self.k8s_client.deployment_replicas[key], deployment.spec.replicas)

        # Check that the annotation was set via API call
        self.k8s_client.api.patch_namespaced_deployment.assert_called_once_with(
            name=deployment.metadata.name,
            namespace=deployment.metadata.namespace,
            body={"metadata": {"annotations": {
                TARNFUI_REPLICAS_ANNOTATION: str(deployment.spec.replicas)}}}
        )

    def test_get_original_replicas_from_annotation(self):
        """Test getting original replicas from annotation."""
        # Create a deployment with annotation
        annotations = {TARNFUI_REPLICAS_ANNOTATION: "5"}
        deployment = self._create_test_deployment(
            "deployment-with-annotation", "default", 0, annotations)

        original_replicas = self.k8s_client.get_original_replicas(deployment)

        self.assertEqual(original_replicas, 5)

    def test_get_original_replicas_fallback(self):
        """Test fallback to memory cache when annotation is not present."""
        deployment = self._create_test_deployment(
            "deployment-no-annotation", "default", 0)

        # Pre-populate the memory cache
        key = f"{deployment.metadata.namespace}/{deployment.metadata.name}"
        self.k8s_client.deployment_replicas[key] = 4

        original_replicas = self.k8s_client.get_original_replicas(deployment)

        self.assertEqual(original_replicas, 4)

    def test_get_original_replicas_none(self):
        """Test when no original replicas info is available."""
        deployment = self._create_test_deployment(
            "deployment-unknown", "default", 0)

        original_replicas = self.k8s_client.get_original_replicas(deployment)

        self.assertIsNone(original_replicas)

    def test_scale_deployment(self):
        """Test scaling a deployment to a specific number of replicas."""
        deployment = self.test_deployments[0]
        new_replicas = 0

        self.k8s_client.scale_deployment(deployment, new_replicas)

        # Check that state was saved when scaling to 0
        key = f"{deployment.metadata.namespace}/{deployment.metadata.name}"
        self.assertIn(key, self.k8s_client.deployment_replicas)

        # Check that the deployment was scaled
        self.k8s_client.api.patch_namespaced_deployment.assert_any_call(
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

        # Create deployments with 0 replicas but different annotation states
        deployment1 = self._create_test_deployment(
            "deployment1", "default", 0,
            annotations={TARNFUI_REPLICAS_ANNOTATION: "3"}
        )
        deployment2 = self._create_test_deployment(
            "deployment2", "default", 0
        )

        self.k8s_client.api.list_namespaced_deployment.return_value.items = [
            deployment1, deployment2]

        # Pre-populate the memory cache for the second deployment
        self.k8s_client.deployment_replicas["default/deployment2"] = 2

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

    def test_start_deployments_no_saved_state(self):
        """Test starting deployments with no saved state defaults to 1 replica."""
        namespace = "default"
        deployment = self._create_test_deployment(
            "unknown-deployment", "default", 0)

        self.k8s_client.api.list_namespaced_deployment.return_value.items = [
            deployment]

        self.k8s_client.start_deployments(namespace)

        # Verify that the deployment was scaled to 1 replica by default
        self.k8s_client.api.patch_namespaced_deployment.assert_called_with(
            name="unknown-deployment",
            namespace="default",
            body={"spec": {"replicas": 1}}
        )


if __name__ == "__main__":
    unittest.main()
