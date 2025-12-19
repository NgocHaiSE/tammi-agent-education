import time
import threading
import logging
from concurrent import futures

import grpc
from agent.handlers.grpc_handler import AgentServiceHandler
from agent.proto import agents_pb2, agents_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("e2e")

HOST = '127.0.0.1'
PORT = 50051


def start_server(stop_event, port_holder):
    print('E2E: starting server thread')
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
    agents_pb2_grpc.add_AgentServiceServicer_to_server(AgentServiceHandler(), server)
    bind_addr = f'{HOST}:{PORT}'
    server.add_insecure_port(bind_addr)
    server.start()
    print(f'E2E: server started on {bind_addr}')
    port_holder.append(PORT)
    try:
        while not stop_event.is_set():
            time.sleep(0.1)
    finally:
        server.stop(0)
        print('E2E: server stopped')


def run_client():
    print('E2E: client sleeping briefly to allow server startup')
    time.sleep(0.5)
    print(f'E2E: client connecting to {HOST}:{PORT}')
    channel = grpc.insecure_channel(f'{HOST}:{PORT}')
    stub = agents_pb2_grpc.AgentServiceStub(channel)

    req = agents_pb2.AgentRequest(
        session_id='e2e-s1',
        flow_id='e2e-f1',
        request_id='e2e-r1',
        user_context=agents_pb2.UserContext(user_id='u-e2e', family_id='fam', name='E2E'),
        client_context=agents_pb2.ClientContext(box_id='b1', type_box='dev', device_model='m', os_type='linux', os_version='1.0', app_version='1.0', timestamp=time.strftime('%Y-%m-%dT%H:%M:%SZ')),
        payload=agents_pb2.Payload(type='text', content='Tôi cần ý tưởng cuối tuần', intent='medical', sub_intent='weekend_idea'),
        history=[],
        stream=False,
    )

    print('E2E: client sending request')
    resp = stub.Handle(req, timeout=10)
    print('--- E2E CLIENT RECEIVED RESPONSE ---')
    print('status:', resp.status.code, resp.status.message)
    print('display:', resp.data.payload.display_message)
    print('tts:', resp.data.payload.tts_message)
    print('suggestions:', list(resp.data.payload.suggestions))


if __name__ == '__main__':
    print('E2E: main starting')
    stop_event = threading.Event()
    port_holder = []
    t = threading.Thread(target=start_server, args=(stop_event, port_holder), daemon=True)
    t.start()

    try:
        run_client()
    finally:
        stop_event.set()
        t.join(timeout=2)
        print('E2E: finished')
