# Line 1:  Import urllib.request to make real HTTP calls (stdlib only, no requests library).
import urllib.request

# Line 2:  Import urllib.error to handle HTTP errors gracefully.
import urllib.error

# Line 3:  Import json for serializing request bodies and parsing responses.
import json

# Line 4:  Import time for latency measurement.
import time

# Line 5:  Import typing for type hints.
from typing import Dict, Any

# Line 8:  Import WireRequest and WireResponse from the interceptor module.
from .interceptor import WireRequest, WireResponse


# Line 12:  LiveBackend makes REAL HTTP calls using only the standard library.
class LiveBackend:
    # Line 14:  Constructor takes an API key (optional - if None, calls will fail with 401).
    def __init__(self, api_key: str = "", base_url: str = "https://api.openai.com/v1"):
        # Line 16:  Store the API key for Authorization header.
        self.api_key = api_key
        # Line 17:  Store the base URL (can be pointed at any OpenAI-compatible endpoint).
        self.base_url = base_url

    # Line 20:  Handle a WireRequest by making an actual HTTP POST via urllib.
    def handle(self, request: WireRequest) -> WireResponse:
        # Line 22:  Record start time for latency measurement.
        start_time = time.time()
        # Line 23:  Initialize the response body and status code with defaults.
        status_code = 0
        # Line 24:  Response headers will be populated after the call.
        resp_headers: Dict[str, str] = {}
        # Line 25:  Raw response body as text.
        raw_body = ""

        try:
            # Line 28:  Serialize the request body to JSON bytes (urllib needs bytes).
            data = json.dumps(request.body).encode("utf-8")
            # Line 29:  Build the full URL by combining base_url with the endpoint path.
            full_url = (
                f"{self.base_url}{request.url}"
                if not request.url.startswith("http")
                else request.url
            )
            # Line 30:  Build headers dict, ensuring Content-Type is set.
            headers = dict(request.headers)
            # Line 31:  Always set Content-Type for JSON payloads.
            headers["Content-Type"] = "application/json"
            # Line 32:  Add Authorization header if we have an API key.
            if self.api_key:
                # Line 34:  Bearer token format (standard for most LLM APIs).
                headers["Authorization"] = f"Bearer {self.api_key}"
            # Line 35:  Create the HTTP request object with method, URL, data, and headers.
            http_req = urllib.request.Request(
                full_url, data=data, headers=headers, method="POST"
            )
            # Line 36:  Make the actual network call (this is where real I/O happens).
            http_resp = urllib.request.urlopen(http_req, timeout=30)
            # Line 37:  Read the response body as bytes then decode to string.
            raw_body = http_resp.read().decode("utf-8")
            # Line 38:  Get the status code from the response object.
            status_code = http_resp.status
            # Line 39:  Extract response headers into a dict.
            resp_headers = dict(http_resp.headers)

        except urllib.error.HTTPError as e:
            # Line 42:  HTTP errors (4xx, 5xx) are caught here - they're not exceptions in the "bad" sense.
            status_code = e.code
            # Line 43:  Try to read the error body (APIs often return JSON error details).
            try:
                # Line 45:  Read the error response body.
                raw_body = e.read().decode("utf-8")
            except Exception:
                # Line 48:  If we can't read the body, use the error message as fallback.
                raw_body = str(e)
            # Line 49:  Extract error response headers if available.
            resp_headers = dict(e.headers) if e.headers else {}

        except urllib.error.URLError as e:
            # Line 52:  Connection errors (DNS failure, timeout, refused connection).
            status_code = 0
            # Line 53:  Set raw body to describe the connection problem.
            raw_body = f"Connection error: {str(e.reason)}"
            # Line 54:  No headers available on connection failure.
            resp_headers = {}

        except Exception as e:
            # Line 57:  Catch-all for any other unexpected errors.
            status_code = 0
            # Line 58:  Describe the unexpected error.
            raw_body = f"Unexpected error: {str(e)}"
            # Line 59:  No headers.
            resp_headers = {}

        # Line 62:  Calculate actual latency in milliseconds.
        latency_ms = (time.time() - start_time) * 1000.0

        # Line 64:  Try to parse the raw body as JSON (it might not be valid JSON on errors).
        body_parsed = None
        # Line 65:  Attempt JSON parsing with a fallback.
        try:
            # Line 67:  Parse the JSON response body.
            body_parsed = json.loads(raw_body) if raw_body else None
        except (json.JSONDecodeError, TypeError):
            # Line 70:  If parsing fails, leave body_parsed as None.
            body_parsed = None

        # Line 72:  Determine if this was an error response.
        is_error = status_code != 200 or status_code == 0

        # Line 74:  Construct and return the WireResponse with all collected data.
        return WireResponse(
            # Line 76:  Correlate with the original request.
            request_id=request.request_id,
            # Line 77:  The HTTP status code (0 means connection failed entirely).
            status_code=status_code,
            # Line 78:  Response headers from the server.
            headers=resp_headers,
            # Line 79:  Parsed JSON body (or None if not valid JSON).
            body=body_parsed,
            # Line 80:  The raw text as received over the wire.
            raw_body=raw_body,
            # Line 81:  Measured round-trip latency.
            latency_ms=latency_ms,
            # Line 82:  Whether this was an error condition.
            is_error=is_error,
        )
