"""gRPC test utilities."""

import asyncio
import grpc.aio
from typing import Optional

from agent.proto import agents_pb2, agents_pb2_grpc
from agent.handlers.grpc_handler import AgentServiceHandler


class GrpcServerManager:
    """Helper class to manage test gRPC server lifecycle."""
    
    def __init__(self):
        self.server: Optional[grpc.aio.Server] = None
        self.port: Optional[int] = None
        self.stop_event = asyncio.Event()
    
    async def start(self) -> int:
        """
        Start gRPC server on random available port.
        
        Returns:
            Port number where server is listening
        """
        self.server = grpc.aio.server()
        agents_pb2_grpc.add_AgentServiceServicer_to_server(
            AgentServiceHandler(), 
            self.server
        )
        
        # Bind to random available port
        self.port = self.server.add_insecure_port('127.0.0.1:0')
        await self.server.start()
        
        return self.port
    
    async def stop(self, grace: float = 0.5) -> None:
        """
        Stop the gRPC server.
        
        Args:
            grace: Grace period in seconds for shutdown
        """
        if self.server:
            self.stop_event.set()
            await self.server.stop(grace=grace)
            self.server = None
            self.port = None
    
    async def __aenter__(self):
        """Context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.stop()


async def create_test_grpc_channel(port: int) -> grpc.aio.Channel:
    """
    Create a gRPC channel for testing.
    
    Args:
        port: Port number to connect to
        
    Returns:
        Async gRPC channel
    """
    return grpc.aio.insecure_channel(f'127.0.0.1:{port}')


def create_test_agent_request(
    content: str = "Test message",
    sub_intent: str = "general",
    stream: bool = False
) -> agents_pb2.AgentRequest:
    """
    Create a test AgentRequest protobuf message.
    
    Args:
        content: Message content
        sub_intent: Intent classification
        stream: Whether to request streaming response
        
    Returns:
        AgentRequest protobuf message
    """
    return agents_pb2.AgentRequest(
        session_id='test-session',
        flow_id='test-flow',
        request_id='test-request',
        user_context=agents_pb2.UserContext(user_id='test-user'),
        client_context=agents_pb2.ClientContext(),
        payload=agents_pb2.Payload(
            type='text',
            content=content,
            intent='medical',
            sub_intent=sub_intent,
            metadata=agents_pb2.Metadata()
        ),
        stream=stream
    )
