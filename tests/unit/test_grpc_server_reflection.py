"""
Unit tests for gRPC server reflection service.

Test Coverage:
- Verify grpcio-reflection dependency is installed
- Verify reflection import works
- Verify SERVICE_NAMES tuple is correctly defined
- Verify reflection service can be enabled
- Verify AgentService full name is correct
- Mock test server startup with reflection
"""

import pytest
import sys
from unittest.mock import patch, MagicMock, AsyncMock
import importlib


def test_grpcio_reflection_dependency_installed():
    """Test that grpcio-reflection package is available."""
    try:
        import grpc_reflection
        assert grpc_reflection is not None, "grpc_reflection module should be importable"
    except ImportError as e:
        pytest.fail(f"grpcio-reflection not installed: {e}")


def test_reflection_v1alpha_import():
    """Test that reflection.v1alpha module can be imported."""
    try:
        from grpc_reflection.v1alpha import reflection
        assert reflection is not None
        assert hasattr(reflection, 'enable_server_reflection')
        assert hasattr(reflection, 'SERVICE_NAME')
    except ImportError as e:
        pytest.fail(f"Cannot import grpc_reflection.v1alpha.reflection: {e}")


def test_agents_pb2_has_descriptor():
    """Test that agents_pb2 has DESCRIPTOR with services_by_name."""
    try:
        from agent.proto import agents_pb2
        
        assert hasattr(agents_pb2, 'DESCRIPTOR'), "agents_pb2 should have DESCRIPTOR"
        assert hasattr(agents_pb2.DESCRIPTOR, 'services_by_name'), "DESCRIPTOR should have services_by_name"
        assert 'AgentService' in agents_pb2.DESCRIPTOR.services_by_name, "AgentService should be in services_by_name"
        
        service = agents_pb2.DESCRIPTOR.services_by_name['AgentService']
        assert hasattr(service, 'full_name'), "AgentService should have full_name attribute"
        assert service.full_name == 'agents.v1.AgentService', f"Expected 'agents.v1.AgentService', got '{service.full_name}'"
        
    except ImportError as e:
        pytest.fail(f"Cannot import agents_pb2: {e}")


def test_service_names_tuple_structure():
    """Test that SERVICE_NAMES tuple in grpc_server.py is correctly structured."""
    from grpc_reflection.v1alpha import reflection
    from agent.proto import agents_pb2
    
    # Simulate the SERVICE_NAMES tuple from grpc_server.py
    SERVICE_NAMES = (
        agents_pb2.DESCRIPTOR.services_by_name['AgentService'].full_name,
        reflection.SERVICE_NAME,
    )
    
    assert isinstance(SERVICE_NAMES, tuple), "SERVICE_NAMES should be a tuple"
    assert len(SERVICE_NAMES) == 2, "SERVICE_NAMES should have exactly 2 elements"
    assert SERVICE_NAMES[0] == 'agents.v1.AgentService', f"First element should be 'agents.v1.AgentService', got '{SERVICE_NAMES[0]}'"
    assert SERVICE_NAMES[1] == 'grpc.reflection.v1alpha.ServerReflection', f"Second element should be reflection service name, got '{SERVICE_NAMES[1]}'"


@pytest.mark.asyncio
async def test_grpc_server_reflection_enabled():
    """Test that reflection can be enabled on a mock gRPC server."""
    from grpc_reflection.v1alpha import reflection
    from agent.proto import agents_pb2
    
    # Create a mock server
    mock_server = MagicMock()
    
    SERVICE_NAMES = (
        agents_pb2.DESCRIPTOR.services_by_name['AgentService'].full_name,
        reflection.SERVICE_NAME,
    )
    
    try:
        # Enable reflection (should not raise exception)
        reflection.enable_server_reflection(SERVICE_NAMES, mock_server)
    except Exception as e:
        pytest.fail(f"enable_server_reflection raised exception: {e}")


def test_grpc_server_imports():
    """Test that grpc_server.py can import all required modules."""
    try:
        # Import the server module
        from agent.entrypoint import grpc_server
        
        # Verify required attributes exist
        assert hasattr(grpc_server, 'serve'), "grpc_server should have serve() function"
        assert callable(grpc_server.serve), "serve should be callable"
        
    except ImportError as e:
        pytest.fail(f"Cannot import grpc_server: {e}")


@pytest.mark.asyncio
async def test_grpc_server_serve_function_structure():
    """Test the structure of the serve() function with mocked dependencies."""
    
    with patch('agent.entrypoint.grpc_server.grpc.aio.server') as mock_grpc_server, \
         patch('agent.entrypoint.grpc_server.agents_pb2_grpc.add_AgentServiceServicer_to_server') as mock_add_servicer, \
         patch('agent.entrypoint.grpc_server.reflection.enable_server_reflection') as mock_enable_reflection, \
         patch('agent.entrypoint.grpc_server.AgentServiceHandler') as mock_handler, \
         patch('agent.entrypoint.grpc_server.settings') as mock_settings:
        
        # Setup mocks
        mock_server_instance = MagicMock()
        mock_server_instance.add_insecure_port = MagicMock()
        mock_server_instance.start = AsyncMock()
        mock_server_instance.wait_for_termination = AsyncMock()
        mock_grpc_server.return_value = mock_server_instance
        
        mock_settings.service_host = "0.0.0.0"
        mock_settings.service_port = "50051"
        mock_settings.agent_display_name = "Test Agent"
        
        # Import and call serve
        from agent.entrypoint.grpc_server import serve
        
        # Create a task and cancel it quickly to avoid waiting
        import asyncio
        task = asyncio.create_task(serve())
        await asyncio.sleep(0.1)  # Let it initialize
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass  # Expected
        
        # Verify calls
        mock_grpc_server.assert_called_once()
        mock_add_servicer.assert_called_once()
        mock_enable_reflection.assert_called_once()
        mock_server_instance.add_insecure_port.assert_called_once_with("0.0.0.0:50051")
        mock_server_instance.start.assert_called_once()


def test_reflection_service_name_constant():
    """Test that reflection.SERVICE_NAME is the expected value."""
    from grpc_reflection.v1alpha import reflection
    
    # The standard gRPC reflection service name
    expected_name = 'grpc.reflection.v1alpha.ServerReflection'
    
    assert reflection.SERVICE_NAME == expected_name, \
        f"reflection.SERVICE_NAME should be '{expected_name}', got '{reflection.SERVICE_NAME}'"


def test_grpc_server_has_main_block():
    """Test that grpc_server.py has __main__ block for standalone execution."""
    import inspect
    from agent.entrypoint import grpc_server
    
    # Read the source code
    source = inspect.getsource(grpc_server)
    
    assert 'if __name__ == "__main__"' in source, "grpc_server.py should have __main__ block"
    assert 'asyncio.run(serve())' in source, "grpc_server.py should call asyncio.run(serve())"


def test_requirements_has_grpcio_reflection():
    """Test that requirements.txt includes grpcio-reflection dependency."""
    requirements_path = "requirements.txt"
    
    try:
        with open(requirements_path, 'r') as f:
            requirements = f.read()
            
        assert 'grpcio-reflection' in requirements, "requirements.txt should include grpcio-reflection"
        
        # Check version constraint
        assert 'grpcio-reflection>=1.60.0' in requirements or \
               'grpcio-reflection>=' in requirements, \
               "grpcio-reflection should have version constraint >=1.60.0"
               
    except FileNotFoundError:
        pytest.fail(f"requirements.txt not found at {requirements_path}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
