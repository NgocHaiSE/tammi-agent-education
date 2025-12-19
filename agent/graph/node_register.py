"""
Node registration and discovery system.

Provides decorators and utilities for registering nodes with the graph
and managing their lifecycle.

Enhanced with metadata support for dynamic graph building.
"""

import logging
from typing import Any, Callable, Dict, Optional, Type, List
from dataclasses import dataclass

from agent.graph.node_base import NodeBase

logger = logging.getLogger(__name__)


# ============================================================================
# Node Metadata
# ============================================================================

@dataclass
class NodeMetadata:
    """
    Metadata that each node declares.

    Tells graph:
    - What data types this node produces (weather_data, restaurant_data, etc.)
    - What builders it needs (ui, params, suggestions)
    - Whether suggestions should run in parallel

    This enables dynamic graph construction without hardcoding.
    """
    node_name: str
    priority: int
    produces_data_types: List[str]  # ["weather_data", "restaurant_data"]
    needs_builders: List[str]       # ["ui", "params", "suggestions"]
    parallel_suggestions: bool = True  # Run suggestions in parallel?


# Global node registry
_NODE_REGISTRY: Dict[str, Dict[str, Any]] = {}
_NODE_INSTANCES: Dict[str, NodeBase] = {}


def node_register(
    name: Optional[str] = None,
    priority: int = 0,
    produces: Optional[List[str]] = None,
    needs_builders: Optional[List[str]] = None,
    parallel_suggestions: bool = True,
) -> Callable[[Type[NodeBase]], Type[NodeBase]]:
    """
    Decorator to register a node class with metadata.

    Enhanced to support metadata-driven graph construction.
    Nodes declare what they produce and what builders they need.

    Args:
        name: Node identifier (default: class name in snake_case)
        priority: Execution priority (higher = earlier)
        produces: List of data types this node produces
                 Examples: ["weather_data"], ["weather_data", "restaurant_data"]
        needs_builders: List of builder types needed
                       Examples: ["ui", "params"], ["ui", "params", "suggestions"]
        parallel_suggestions: Whether suggestions should run in parallel with node

    Returns:
        Decorator function
        
    Example:
        >>> @node_register(
        ...     name="outfit_suggestion",
        ...     priority=10,
        ...     produces=["weather_data"],
        ...     needs_builders=["ui", "params", "suggestions"]
        ... )
        ... class OutfitSuggestionNode(NodeBase):
        ...     async def run(self, state):
        ...         weather_data = await fetch_weather()
        ...         return {
        ...             "node_responses": [...],
        ...             "data_artifacts": {"weather_data": weather_data}
        ...         }
    """
    
    def decorator(node_class: Type[NodeBase]) -> Type[NodeBase]:
        # Use provided name or derive from class name
        node_name = name or _camel_to_snake(node_class.__name__)
        
        # Create metadata
        metadata = NodeMetadata(
            node_name=node_name,
            priority=priority,
            produces_data_types=produces or [],
            needs_builders=needs_builders or [],
            parallel_suggestions=parallel_suggestions
        )

        # Store metadata on class
        node_class._node_name = node_name
        node_class._node_priority = priority
        node_class._node_metadata = metadata

        # Register in global registry
        _NODE_REGISTRY[node_name] = {
            "class": node_class,
            "priority": priority,
            "metadata": metadata
        }

        logger.info(
            f"Registered node '{node_name}' "
            f"(class: {node_class.__name__}, priority: {priority}, "
            f"produces: {produces or []}, needs_builders: {needs_builders or []})"
        )
        
        return node_class
    
    return decorator


def get_node_class(name: str) -> Optional[Type[NodeBase]]:
    """
    Get a registered node class by name.
    
    Args:
        name: Node name
        
    Returns:
        Node class or None if not found
    """
    node_info = _NODE_REGISTRY.get(name)
    return node_info["class"] if node_info else None


def get_node_instance(
    name: str,
    *args: Any,
    recreate: bool = False,
    **kwargs: Any,
) -> Optional[NodeBase]:
    """Lấy (và cache) instance của một node đã đăng ký.

    Mặc định: nếu instance đã tồn tại thì trả về lại (singletons nhẹ theo tên).
    Nếu cần tạo mới, truyền recreate=True.

    Args:
        name: Tên node đã đăng ký (snake_case)
        *args, **kwargs: Tham số truyền vào constructor của node class
        recreate: True để buộc tạo mới thay vì dùng cache

    Returns:
        Instance của node hoặc None nếu không tìm thấy / lỗi khởi tạo

    Ví dụ:
        >>> agent_node = get_node_instance("health_advice", llm=my_llm)
        >>> agent_node.run(state)
    """
    cls = get_node_class(name)
    if cls is None:
        logger.warning(f"get_node_instance: Node '{name}' chưa được đăng ký.")
        return None

    if not recreate and name in _NODE_INSTANCES:
        return _NODE_INSTANCES[name]

    try:
        instance = cls(*args, **kwargs)
    except TypeError as e:
        logger.error(
            f"Không thể khởi tạo node '{name}' với args={args} kwargs={kwargs}: {e}",
            exc_info=True,
        )
        return None
    except Exception as e:
        logger.error(
            f"Lỗi không xác định khi khởi tạo node '{name}': {e}",
            exc_info=True,
        )
        return None

    _NODE_INSTANCES[name] = instance
    logger.info(f"Tạo mới instance cho node '{name}' (recreate={recreate}).")
    return instance


def get_node_metadata(name: str) -> Optional[NodeMetadata]:
    """
    Get metadata for a registered node.

    Args:
        name: Node name

    Returns:
        NodeMetadata or None if not found
    """
    node_info = _NODE_REGISTRY.get(name)
    return node_info["metadata"] if node_info else None


def list_nodes() -> list[Dict[str, Any]]:
    """
    List all registered nodes with their metadata.

    Returns:
        List of dicts containing node info:
        [
            {
                "name": "outfit_suggestion",
                "class": OutfitSuggestionNode,
                "priority": 10,
                "metadata": NodeMetadata(...)
            },
            ...
        ]
    """
    nodes = []
    for name, info in _NODE_REGISTRY.items():
        nodes.append({
            "name": name,
            "class": info["class"],
            "priority": info["priority"],
            "metadata": info["metadata"]
        })

    # Sort by priority (descending)
    nodes.sort(key=lambda x: x["priority"], reverse=True)

    return nodes



def unregister_node(name: str) -> bool:
    """
    Unregister a node from the registry.
    
    Args:
        name: Node name
        
    Returns:
        True if unregistered, False if not found
    """
    if name in _NODE_REGISTRY:
        del _NODE_REGISTRY[name]
        logger.info(f"Unregistered node '{name}'")
        # Xóa luôn instance cache nếu có
        if name in _NODE_INSTANCES:
            del _NODE_INSTANCES[name]
            logger.info(f"Deleted cached instance for node '{name}'")
        return True
    return False


def clear_registry() -> None:
    """Clear all registered nodes (useful for testing)."""
    _NODE_REGISTRY.clear()
    logger.info("Cleared node registry")
    _NODE_INSTANCES.clear()
    logger.info("Cleared node instances cache")


def _camel_to_snake(name: str) -> str:
    """
    Convert CamelCase to snake_case.
    
    Args:
        name: CamelCase string
        
    Returns:
        snake_case string
        
    Example:
        >>> _camel_to_snake("FoodSuggestionNode")
        'food_suggestion_node'
    """
    result = []
    for i, char in enumerate(name):
        if char.isupper() and i > 0:
            result.append('_')
            result.append(char.lower())
        else:
            result.append(char.lower())
    return ''.join(result)


def _snake_to_camel(name: str) -> str:
    """
    Convert snake_case to CamelCase.
    
    Args:
        name: snake_case string
        
    Returns:
        CamelCase string
        
    Example:
        >>> _snake_to_camel("food_suggestion")
        'FoodSuggestion'
    """
    components = name.split('_')
    return ''.join(x.title() for x in components)
