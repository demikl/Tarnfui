"""Kubernetes client module for Tarnfui.

This module handles all interactions with the Kubernetes API.
"""

import logging

from tarnfui.kubernetes.controller import KubernetesController

logger = logging.getLogger(__name__)

# Export KubernetesController as the main interface
__all__ = [
    "KubernetesController",
]
