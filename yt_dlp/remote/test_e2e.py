import time
import threading
import queue
import logging
import json
import requests
import grpc

from yt_dlp.protogen.ytdlp.v1 import reverse_executor_pb2, reverse_executor_pb2_grpc

from yt_dlp.remote.server import serve

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
logger = logging.getLogger('TestClient')


def run_test_client(server_port, video_url):
    channel = grpc.insecure_channel(f'localhost:{server_port}')
    stub = reverse_executor_pb2_grpc.ReverseExecutorStub(channel)

    request_queue = queue.Queue()

    def request_iterator():
        while True:
            msg = request_queue.get()
            if msg is None:
                break
            yield msg

    logger.info('Connecting to server...')

    # Start stream in a separate thread to handle responses
    # Actually, TaskStream is bidirectional. We can iterate responses in main thread
    # and yield requests from generator.

    # Send Hello first
    logger.info('Sending Hello...')
    hello = reverse_executor_pb2.Hello(
        device_id='test-device-001',
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        app_version='1.0.0',
        capabilities={'http_chunking': 'true'},
    )
    request_queue.put(reverse_executor_pb2.ClientMessage(hello=hello))

    # Send TaskRequest
    logger.info(f'Sending TaskRequest for {video_url}...')
    task_id = 'task-001'
    task_req = reverse_executor_pb2.TaskRequest(
        task_id=task_id,
        url=video_url,
        options={
            'quiet': 'true',
            'no_warnings': 'true',
            # "skip_download": "true" # We want extract_info not download, server handles this but good to be explicit if passed to ydl
        },
    )
    request_queue.put(reverse_executor_pb2.ClientMessage(task_request=task_req))

    try:
        responses = stub.TaskStream(request_iterator())

        for msg in responses:
            payload = msg.WhichOneof('payload')

            if payload == 'request':
                req = msg.request
                logger.info(f'Executing remote request: {req.method} {req.url}')

                try:
                    # Execute HTTP request via requests lib
                    headers = dict(req.headers)

                    # Log cookies if present
                    if 'cookie' in headers:
                        logger.debug('Request has cookies')

                    # Perform request
                    resp = requests.request(
                        method=req.method,
                        url=req.url,
                        headers=headers,
                        data=req.body,
                        timeout=req.timeout_ms / 1000.0 if req.timeout_ms > 0 else 30,
                        allow_redirects=req.follow_redirects,
                    )

                    logger.info(f'Request complete: {resp.status_code} len={len(resp.content)}')

                    # Send response back
                    client_resp = reverse_executor_pb2.HttpResponse(
                        request_id=req.request_id,
                        task_id=req.task_id,
                        status=resp.status_code,
                        headers=dict(resp.headers),
                        body=resp.content,
                        final_url=resp.url,
                    )
                    request_queue.put(reverse_executor_pb2.ClientMessage(response=client_resp))

                except Exception as e:
                    logger.error(f'Request failed: {e}')
                    err = reverse_executor_pb2.Error(
                        request_id=req.request_id,
                        code='HTTP_ERROR',
                        message=str(e),
                    )
                    request_queue.put(reverse_executor_pb2.ClientMessage(error=err))

            elif payload == 'extract_result':
                result = msg.extract_result
                logger.info(f'Got ExtractResult for task {result.task_id}')

                try:
                    info = json.loads(result.info_json.decode('utf-8'))
                    title = info.get('title')
                    duration = info.get('duration')
                    logger.info(f'Video Title: {title}')
                    logger.info(f'Duration: {duration}')

                    if title:
                        logger.info('TEST PASSED: Successfully extracted video info')
                    else:
                        logger.error('TEST FAILED: No title in result')

                except Exception as e:
                    logger.error(f'Failed to parse result JSON: {e}')

                request_queue.put(None)  # Stop client
                return

            elif payload == 'task_accepted':
                logger.info(f'Task accepted: {msg.task_accepted.message}')

            elif payload == 'error':
                logger.error(f'Server sent error: {msg.error.message}')
                request_queue.put(None)
                return

            elif payload == 'ping':
                # Respond to ping
                request_queue.put(reverse_executor_pb2.ClientMessage(
                    pong=reverse_executor_pb2.Pong(nonce=msg.ping.nonce),
                ))

    except grpc.RpcError as e:
        logger.error(f'RPC Error: {e}')
    except Exception as e:
        logger.error(f'Client Error: {e}')
    finally:
        request_queue.put(None)


def main():
    port = 50052

    # Start server in background thread
    logger.info(f'Starting server on port {port}...')
    server_thread = threading.Thread(target=serve, args=(port,), daemon=True)
    server_thread.start()
    time.sleep(2)  # Wait for server start

    # URL to test. Using 'Me at the zoo' as it's short and stable.
    url = 'https://www.youtube.com/watch?v=jNQXAC9IVRw'

    run_test_client(port, url)


if __name__ == '__main__':
    main()
