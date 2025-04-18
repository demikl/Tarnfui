"""Kubernetes client module for Tarnfui.

This module handles all interactions with the Kubernetes API.
"""

import logging

from tarnfui.kubernetes.controller import KubernetesController

logger = logging.getLogger(__name__)

# Constants for event types
EVENT_TYPE_NORMAL = "Normal"
EVENT_TYPE_WARNING = "Warning"
# Constants for event reasons
EVENT_REASON_STOPPED = "Stopped"
EVENT_REASON_STARTED = "Started"
# Component name for events
EVENT_COMPONENT = "tarnfui"
# Key used for storing replica count in deployment annotations
TARNFUI_REPLICAS_ANNOTATION = "tarnfui.io/original-replicas"

# Export KubernetesController as the main interface
__all__ = [
    "KubernetesController",
    "EVENT_TYPE_NORMAL",
    "EVENT_TYPE_WARNING",
    "EVENT_REASON_STOPPED",
    "EVENT_REASON_STARTED",
    "EVENT_COMPONENT",
    "TARNFUI_REPLICAS_ANNOTATION",
]
