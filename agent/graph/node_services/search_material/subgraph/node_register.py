"""Node registration module for the Search Material Assistant Subgraph.
This module provides a decorator to register node classes implementing
`SearchMaterialNodeInterface` into a central registry, as well as a function
to retrieve all registered nodes.
The registry is used when building the state graph for the Search Material
Agent to determine which nodes are available and how they connect.
"""

import logging

from typing import Any, Dict
from agent.graph.node_services.search_material.subgraph.node_interface import HealthAdviceNodeInterface

logger = logging.getLogger(__name__)

__nodes_register: Dict[str, HealthAdviceNodeInterface] = {}


def register_node(node_class: HealthAdviceNodeInterface):
    """Register a node class into the global node registry.
    This function is intended to be used as a class decorator. The node
    class must inherit from `HealthAdviceNodeInterface`, define a class
    attribute `name`, and implement a callable `run` method.
    Args:
        node_class (HealthAdviceNodeInterface): The node class to register.
    Returns:
        HealthAdviceNodeInterface: The original node class, unmodified.
    Raises:
        TypeError: If `node_class` is not a subclass of HealthAdviceNodeInterface.
        AttributeError: If `node_class` does not have a `name` attribute.
        AttributeError: If `node_class` does not have a callable `run` method.
    """
    if not issubclass(node_class, HealthAdviceNodeInterface):
        raise TypeError(f"{node_class.__name__} must be a subclass of HealthAdviceNodeInterface")

    if not hasattr(node_class, 'name'):
        raise AttributeError(f"{node_class.__name__} must have a 'name' attribute")

    if not hasattr(node_class, 'run') or not callable(node_class.run):
        raise AttributeError(f"{node_class.__name__} must have a callable 'run' method")

    __nodes_register[node_class.name] = node_class
    return node_class


def get_nodes_register():
    """Retrieve the dictionary of all registered nodes.
    Returns:
        dict[str, HealthAdviceNodeInterface]: Mapping of node names to
        their corresponding node classes.
    """
    return __nodes_register