"""
ReverseExecutor gRPC server.

Purpose
-------
Some deployment targets (for example, iOS devices on restricted networks)
cannot allow yt-dlp to issue HTTP requests directly. ReverseExecutor flips the
model: yt-dlp runs on the server, but every network fetch is delegated to a
remote client over gRPC. This keeps yt-dlp's parsing logic and output intact
while ensuring all external traffic originates from the client device.

Usage
-----
1. Ensure protobuf stubs are generated (see protogen/README).
2. Install dependencies: `pip install .[remote]` inside the yt-dlp repo.
3. Run the server: `python -m yt_dlp.remote.server --port 50051` (default 50051).
4. Connect a client (for example, `python -m yt_dlp.remote.test_e2e`) which:
   - Opens a `TaskStream` bidi RPC
   - Sends a Hello message describing device/user-agent/cookies
   - Receives download/extract tasks and performs HTTP requests locally
5. The client forwards HTTP responses back to the server so yt-dlp can
   complete extraction without touching the remote network directly.

See `yt_dlp/remote/test_e2e.py` for a minimal reference client.
"""

import argparse
import logging
import queue
import threading
import time
import uuid
import json
import traceback
import tempfile
import http.cookiejar
from concurrent import futures
from typing import Dict, Optional, Any
import os

import grpc

from yt_dlp.protogen.ytdlp.v1 import reserse_executor_pb2, reserse_executor_pb2_grpc

from yt_dlp import YoutubeDL
from yt_dlp.cookies import YoutubeDLCookieJar

logger = logging.getLogger(__name__)

class RequestFuture:
    def __init__(self):
        self.event = threading.Event()
        self.response = None
        self.chunks = []
        self.error = None

class ReverseExecutorServicer(reserse_executor_pb2_grpc.ReverseExecutorServicer):
    def __init__(self, debug_printtraffic: bool = False):
        self._request_queues: Dict[str, queue.Queue] = {}  # connection_id -> Queue[ServerMessage]
        self._pending_requests: Dict[str, RequestFuture] = {}  # request_id -> RequestFuture
        self._client_contexts: Dict[str, Dict[str, Any]] = {} # connection_id -> context dict
        self._lock = threading.Lock()
        self._debug_printtraffic = debug_printtraffic
        
    def TaskStream(self, request_iterator, context):
        connection_id = str(uuid.uuid4())
        response_queue = queue.Queue()
        
        logger.info(f"New connection: {connection_id}")
        
        with self._lock:
            self._request_queues[connection_id] = response_queue
            self._client_contexts[connection_id] = {}

        # Thread to consume requests from client
        def consume_requests():
            try:
                for msg in request_iterator:
                    self._handle_client_message(connection_id, msg)
            except Exception as e:
                logger.error(f"Error reading client stream for {connection_id}: {e}")
            finally:
                response_queue.put(None) # Signal exit

        consumer_thread = threading.Thread(target=consume_requests, daemon=True)
        consumer_thread.start()

        try:
            while True:
                msg = response_queue.get()
                if msg is None:
                    break
                yield msg
        finally:
            logger.info(f"Connection closed: {connection_id}")
            with self._lock:
                if connection_id in self._request_queues:
                    del self._request_queues[connection_id]
                if connection_id in self._client_contexts:
                    del self._client_contexts[connection_id]
            # Cancel any pending requests for this connection? 
            # Ideally yes, but complex tracking needed.

    def _handle_client_message(self, connection_id: str, msg: reserse_executor_pb2.ClientMessage):
        payload_type = msg.WhichOneof('payload')
        
        if payload_type == 'hello':
            self._handle_hello(connection_id, msg.hello)
        elif payload_type == 'task_request':
            self._handle_task_request(connection_id, msg.task_request)
        elif payload_type == 'response':
            self._handle_http_response(msg.response)
        elif payload_type == 'chunk':
            self._handle_http_chunk(msg.chunk)
        elif payload_type == 'error':
            self._handle_error(msg.error)
        elif payload_type == 'pong':
            logger.debug(f"Received Pong from {connection_id}")

    def _handle_hello(self, connection_id: str, hello: reserse_executor_pb2.Hello):
        logger.info(f"Hello from {connection_id}: {hello.device_id} (UA: {hello.user_agent})")
        with self._lock:
            self._client_contexts[connection_id] = {
                'device_id': hello.device_id,
                'user_agent': hello.user_agent,
                'cookies': hello.cookies,
                'capabilities': hello.capabilities
            }

    def _handle_task_request(self, connection_id: str, request: reserse_executor_pb2.TaskRequest):
        logger.info(f"Received task {request.task_id} for {request.url}")
        
        # Acknowledge task
        self._send_server_message(connection_id, reserse_executor_pb2.ServerMessage(
            task_accepted=reserse_executor_pb2.TaskAccepted(
                task_id=request.task_id,
                message="Task accepted"
            )
        ))
        
        # Retrieve context
        with self._lock:
            ctx = self._client_contexts.get(connection_id, {})

        # Run yt-dlp in a separate thread
        def run_task():
            cookie_file_path = None
            try:
                # Prepare options
                opts = {
                    'logger': logger,
                    # Inject servicer and connection_id for the network handler
                    '_remote_servicer': self,
                    '_connection_id': connection_id,
                    '_task_id': request.task_id,
                }
                if self._debug_printtraffic:
                    opts['debug_printtraffic'] = True
                # Default options suitable for remote execution
                    # 'quiet': True,
                    # 'no_warnings': True,
                
                
                # Apply User-Agent
                if ctx.get('user_agent'):
                    opts['user_agent'] = ctx['user_agent']
                
                # Apply Cookies
                proto_cookies = ctx.get('cookies')
                if proto_cookies:
                    try:
                        fd, cookie_file_path = tempfile.mkstemp(suffix='.txt', prefix='yt_dlp_cookies_')
                        os.close(fd)
                        
                        jar = YoutubeDLCookieJar(cookie_file_path)
                        for c in proto_cookies:
                            # Map proto cookie to http.cookiejar.Cookie
                            py_cookie = http.cookiejar.Cookie(
                                version=0,
                                name=c.name,
                                value=c.value,
                                port=None,
                                port_specified=False,
                                domain=c.domain,
                                domain_specified=bool(c.domain),
                                domain_initial_dot=c.domain.startswith('.'),
                                path=c.path,
                                path_specified=bool(c.path),
                                secure=c.secure,
                                expires=c.expires_unix if c.expires_unix > 0 else None,
                                discard=False,
                                comment=None,
                                comment_url=None,
                                rest={'HttpOnly': c.http_only} if c.http_only else {}
                            )
                            jar.set_cookie(py_cookie)
                        
                        jar.save()
                        opts['cookiefile'] = cookie_file_path
                        logger.info(f"Created temporary cookie file: {cookie_file_path}")
                    except Exception as e:
                        logger.error(f"Failed to setup cookies: {e}")

                # Add options from request
                if request.options:
                    # Caution: blindly applying options might be unsafe or unsupported
                    # For now, let's assume options maps to ydl params
                    opts.update(request.options)

                with YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(request.url, download=False)
                    
                    # Send result
                    if info:
                        info_json = json.dumps(info).encode('utf-8')
                        self._send_server_message(connection_id, reserse_executor_pb2.ServerMessage(
                            extract_result=reserse_executor_pb2.ExtractResult(
                                task_id=request.task_id,
                                info_json=info_json
                            )
                        ))
                    else:
                        # TODO: Handle no info?
                        pass
                        
            except Exception as e:
                logger.error(f"Task {request.task_id} failed: {e}")
                traceback.print_exc()
                self._send_server_message(connection_id, reserse_executor_pb2.ServerMessage(
                    error=reserse_executor_pb2.Error(
                        task_id=request.task_id,
                        code="TASK_FAILED",
                        message=str(e)
                    )
                ))
            finally:
                if cookie_file_path and os.path.exists(cookie_file_path):
                    try:
                        os.remove(cookie_file_path)
                    except OSError:
                        pass

        threading.Thread(target=run_task, daemon=True).start()

    def _handle_http_response(self, response: reserse_executor_pb2.HttpResponse):
        req_id = response.request_id
        with self._lock:
            future = self._pending_requests.get(req_id)
        
        if future:
            future.response = response
            future.event.set()

    def _handle_http_chunk(self, chunk: reserse_executor_pb2.HttpChunk):
        req_id = chunk.request_id
        with self._lock:
            future = self._pending_requests.get(req_id)
        
        if future:
            future.chunks.append(chunk.bytes)
            if chunk.eof:
                future.event.set()

    def _handle_error(self, error: reserse_executor_pb2.Error):
        if error.request_id:
            with self._lock:
                future = self._pending_requests.get(error.request_id)
            if future:
                future.error = error
                future.event.set()
        else:
            logger.error(f"Received generic error: {error.message}")

    def _send_server_message(self, connection_id: str, msg: reserse_executor_pb2.ServerMessage):
        with self._lock:
            q = self._request_queues.get(connection_id)
        if q:
            q.put(msg)
    
    def submit_request(self, connection_id: str, task_id: str, request: reserse_executor_pb2.HttpRequest) -> RequestFuture:
        """Called by ReverseExecutorRequestHandler to send a request"""
        future = RequestFuture()
        with self._lock:
            self._pending_requests[request.request_id] = future
        
        msg = reserse_executor_pb2.ServerMessage(request=request)
        self._send_server_message(connection_id, msg)
        
        return future
    
    def remove_future(self, request_id: str):
        with self._lock:
            if request_id in self._pending_requests:
                del self._pending_requests[request_id]

def serve(port=50051, debug_printtraffic: bool = False):
    if not reserse_executor_pb2_grpc:
        logger.error("gRPC modules not loaded, cannot start server")
        return

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    reserse_executor_pb2_grpc.add_ReverseExecutorServicer_to_server(
        ReverseExecutorServicer(debug_printtraffic=debug_printtraffic), server
    )
    server.add_insecure_port(f'[::]:{port}')
    logger.info(f"Starting ReverseExecutor server on port {port}")
    server.start()
    server.wait_for_termination()

def _parse_log_level(value: str) -> int:
    if value.isdigit():
        return int(value)
    upper = value.upper()
    if upper in logging._nameToLevel:
        return logging._nameToLevel[upper]
    raise argparse.ArgumentTypeError(f"Invalid log level: {value}")


def main():
    parser = argparse.ArgumentParser(description="ReverseExecutor gRPC server")
    parser.add_argument('--port', type=int, default=50051, help='Port to listen on')
    parser.add_argument('--log-level', type=_parse_log_level, default=logging.INFO,
                        help='Logging level (name like INFO/DEBUG or integer)')
    parser.add_argument('--debug-printtraffic', action='store_true',
                        help='Enable YoutubeDL debug_printtraffic option')
    args = parser.parse_args()

    logging.basicConfig(level=args.log_level)
    serve(port=args.port, debug_printtraffic=args.debug_printtraffic)


if __name__ == '__main__':
    main()
