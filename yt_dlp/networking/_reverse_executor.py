from __future__ import annotations

import io
import logging

from .common import (
    RequestHandler,
    Response,
    Request,
    register_rh,
    Features,
)
from .exceptions import (
    RequestError,
    TransportError,
    UnsupportedRequest,
)

logger = logging.getLogger(__name__)

# Import proto definitions
# We assume the server environment has set up paths correctly or this module is used where these are available
from yt_dlp.protogen.ytdlp.v1 import reverse_executor_pb2


@register_rh
class ReverseExecutorRH(RequestHandler):
    """
    RequestHandler that forwards requests to a remote client via ReverseExecutor gRPC service.
    """
    RH_NAME = 'reverse_executor'
    RH_KEY = 'reverse_executor'

    _SUPPORTED_URL_SCHEMES = ('http', 'https')
    _SUPPORTED_FEATURES = (Features.NO_PROXY, Features.ALL_PROXY)
    # Skip proxy check since we're forwarding to client
    _SUPPORTED_PROXY_SCHEMES = None

    def __init__(self, _remote_servicer=None, _connection_id=None, _task_id=None, **kwargs):
        super().__init__(**kwargs)
        self.servicer = _remote_servicer
        self.connection_id = _connection_id
        self.task_id = _task_id
        logger.debug('ReverseExecutorRH initialized (connection=%s, task=%s)', self.connection_id, self.task_id)

    def _validate(self, request):
        if self.servicer is None or self.connection_id is None:
            raise UnsupportedRequest('ReverseExecutor not configured (missing servicer or connection_id)')
        super()._validate(request)

    def _prepare_headers(self, request, headers):
        if 'cookie' not in headers:
            cookiejar = self._get_cookiejar(request)
            cookie_header = cookiejar.get_cookie_header(request.url)
            if cookie_header:
                headers['cookie'] = cookie_header
                logger.debug('Injected cookie header for %s', request.url)
        logger.debug('Prepared headers for %s: %s', request.url, dict(headers))

    def _send(self, request: Request) -> Response:
        # Create unique request ID
        import uuid
        request_id = str(uuid.uuid4())
        logger.debug('Creating remote request %s %s (id=%s)', request.method, request.url, request_id)

        # Prepare headers
        headers = self._get_headers(request)

        # Prepare body
        body = b''
        if request.data:
            if isinstance(request.data, bytes):
                body = request.data
            else:
                # Read all data from stream/iterator
                try:
                    if hasattr(request.data, 'read'):
                        body = request.data.read()
                    else:
                        body = b''.join(request.data)
                except Exception as e:
                    logger.debug('Failed to read body for %s: %s', request_id, e)
                    raise RequestError(f'Failed to read request body: {e}')
        logger.debug('Request %s body length: %d bytes', request_id, len(body))

        # Construct proto request
        proto_req = reverse_executor_pb2.HttpRequest(
            request_id=request_id,
            task_id=self.task_id or '',
            method=request.method,
            url=request.url,
            headers=headers,
            body=body,
            timeout_ms=int(self._calculate_timeout(request) * 1000),
            follow_redirects=True,  # TODO: Make configurable if needed, typically RequestHandler handles redirects?
            # RequestsRH handles redirects internally. urllib doesn't?
            # For now assume client handles redirects.
        )

        # Submit to servicer
        try:
            future = self.servicer.submit_request(self.connection_id, self.task_id, proto_req)
            logger.debug('Submitted remote request %s on connection %s', request_id, self.connection_id)
        except Exception as e:
            logger.debug('Submission failed for %s: %s', request_id, e)
            raise RequestError(f'Failed to submit request to remote executor: {e}')

        # Wait for response
        # We use the timeout from request
        timeout = self._calculate_timeout(request)
        if not future.event.wait(timeout=timeout + 5):  # Give 5s buffer over network timeout
            self.servicer.remove_future(request_id)
            logger.debug('Request %s timed out after %.2fs', request_id, timeout + 5)
            raise TransportError('Request timed out waiting for remote response')

        if future.error:
            # Propagate error
            self.servicer.remove_future(request_id)
            logger.debug('Remote error for %s: %s - %s', request_id, future.error.code, future.error.message)
            raise TransportError(f'Remote error: {future.error.code} - {future.error.message}')

        if future.response:
            resp = future.response
            logger.debug('Received response for %s with status %s', request_id, resp.status)

            # Construct Response object
            # headers is map<string, string>, convert to dict
            resp_headers = dict(resp.headers)

            return Response(
                fp=io.BytesIO(resp.body),
                url=resp.final_url or request.url,
                headers=resp_headers,
                status=resp.status,
                reason=None,  # Will be inferred from status
            )

        if future.chunks:
            # Stitch chunks
            # In a real streaming implementation we might return a generator or custom stream
            # For now, buffer all
            full_body = b''.join(future.chunks)
            logger.debug('Received %d chunks for %s (total=%d bytes)', len(future.chunks), request_id, len(full_body))
            # We don't have headers/status from chunks only?
            # The protocol says: ClientMessage payload can be HttpChunk OR HttpResponse.
            # Usually we expect an HttpResponse HEAD first or eventually?
            # Wait, the current proto definition allows either HttpResponse OR HttpChunk.
            # If we receive Chunks, we might miss Headers if they were sent in a separate message?
            # Our servicer implementation aggregates chunks but doesn't seem to capture the initial response if it came as chunks?
            # Actually ClientMessage `response` is HttpResponse. `chunk` is HttpChunk.
            # If the client sends `response` with body, we use that.
            # If the client sends chunks, it should probably send headers first?
            # The current proto design is:
            # oneof payload { HttpResponse response = 3; HttpChunk chunk = 4; }
            # HttpResponse has `bytes body`.
            # If streaming, maybe HttpResponse comes first with empty body, then chunks follow?
            # The current Servicer implementation sets `future.response` when `response` arrives.
            # It appends chunks when `chunk` arrives.
            # So we likely get response (headers) then chunks.

            if future.response:
                resp = future.response
                resp_headers = dict(resp.headers)
                return Response(
                    fp=io.BytesIO(full_body),
                    url=resp.final_url or request.url,
                    headers=resp_headers,
                    status=resp.status,
                )
            else:
                # Fallback if we only got chunks (unexpected protocol usage)
                self.servicer.remove_future(request_id)
                logger.debug('Received chunks without headers for %s', request_id)
                raise TransportError('Received chunks without response headers')

        self.servicer.remove_future(request_id)
        logger.debug('No response payload received for %s', request_id)
        raise TransportError('No response received')
