# Line 1:  Import dataclasses to define structured wire-level request/response objects.
from dataclasses import dataclass, field

# Line 3:  Import time for latency measurement on the wire.
import time

# Line 4:  Import json for serializing/deserializing wire payloads.
import json

# Line 5:  Import uuid to generate unique request IDs for tracing.
import uuid

# Line 6:  Import typing for type hints (list, dict, Optional).
from typing import List, Dict, Any, Optional


# Line 9:  Define the wire-level HTTP request as a structured object.
@dataclass
class WireRequest:
    # Line 11:  Unique ID to trace this specific request through the system.
    request_id: str = ""
    # Line 12:  HTTP method (always POST for LLM APIs).
    method: str = "POST"
    # Line 13:  Full URL of the API endpoint being called.
    url: str = ""
    # Line 14:  HTTP headers dict (Content-Type, Authorization, etc.).
    headers: Dict[str, str] = field(default_factory=dict)
    # Line 15:  JSON-serializable body that will be sent as the request payload.
    body: Dict[str, Any] = field(default_factory=dict)
    # Line 16:  Timestamp when this request was constructed (for latency calc).
    created_at: float = 0.0

    # Line 19:  Factory method that creates a properly initialized WireRequest.
    @classmethod
    def create(
        cls, url: str, headers: Dict[str, str], body: Dict[str, Any]
    ) -> "WireRequest":
        # Line 21:  Generate a unique ID for this request to correlate with its response.
        req_id = str(uuid.uuid4())[:8]
        # Line 22:  Record the exact moment the request is created (epoch seconds).
        ts = time.time()
        # Line 23:  Return a fully populated WireRequest instance.
        return cls(
            request_id=req_id,
            method="POST",
            url=url,
            headers=headers,
            body=body,
            created_at=ts,
        )


# Line 27:  Define the wire-level HTTP response as a structured object.
@dataclass
class WireResponse:
    # Line 29:  The request ID this response corresponds to (for correlation).
    request_id: str = ""
    # Line 30:  HTTP status code (200=OK, 429=Rate Limited, 500=Server Error).
    status_code: int = 200
    # Line 31:  Response headers from the server.
    headers: Dict[str, str] = field(default_factory=dict)
    # Line 32:  Parsed JSON body from the response (None if not valid JSON).
    body: Optional[Dict[str, Any]] = None
    # Line 33:  Raw text body before JSON parsing (useful for debugging non-JSON errors).
    raw_body: str = ""
    # Line 34:  Total time in milliseconds from request creation to response receipt.
    latency_ms: float = 0.0
    # Line 35:  Whether this response represents an error condition.
    is_error: bool = False


# Line 39:  Define a single intercepted wire event for logging and reporting.
@dataclass
class WireEvent:
    # Line 41:  The full request that was sent.
    request: WireRequest = None
    # Line 42:  The full response that came back (None if connection failed).
    response: Optional[WireResponse] = None
    # Line 43:  Human-readable label for what this call was attempting.
    purpose: str = ""
    # Line 44:  Whether the call succeeded from the agent's perspective.
    success: bool = True


# Line 48:  The Interceptor sits between the agent code and the backend (API server).
class Interceptor:
    # Line 50:  Constructor takes a backend object that implements .handle(WireRequest) -> WireResponse.
    def __init__(self, backend, max_retries: int = 3, retry_delay: float = 1.0):
        # Line 52:  Store the backend (MockBackend or LiveBackend) that actually does the I/O.
        self.backend = backend
        # Line 53:  Maximum number of retries on transient errors (429, 500).
        self.max_retries = max_retries
        # Line 54:  Base delay in seconds between retry attempts (will be backoff-multiplied).
        self.retry_delay = retry_delay
        # Line 55:  List of all WireEvents captured during this interceptor's lifetime.
        self.events: List[WireEvent] = []
        # Line 56:  Running total of prompt tokens consumed across all calls.
        self.total_prompt_tokens: int = 0
        # Line 57:  Running total of completion tokens generated across all calls.
        self.total_completion_tokens: int = 0
        # Line 58:  Count of requests that hit a rate limit (HTTP 429).
        self.rate_limit_count: int = 0
        # Line 59:  Count of requests that hit a server error (HTTP 5xx).
        self.server_error_count: int = 0
        # Line 60:  Count of successful requests (HTTP 200).
        self.success_count: int = 0

    # Line 63:  Send a request through the wire and return the response, with full logging.
    def send(
        self, url: str, headers: Dict[str, str], body: Dict[str, Any], purpose: str = ""
    ) -> WireResponse:
        # Line 65:  Construct the WireRequest object (this is what would go over the network).
        request = WireRequest.create(url=url, headers=headers, body=body)
        # Line 66:  Initialize response variable to None (will be set after backend call).
        response = None
        # Line 67:  Flag to track whether we eventually succeeded.
        success = False
        # Line 68:  Loop for retry logic on transient failures.
        for attempt in range(self.max_retries + 1):
            # Line 70:  Call the backend's handle method (this is where "the wire" happens).
            response = self.backend.handle(request)
            # Line 71:  Check if the response indicates a rate limit (HTTP 429).
            if response.status_code == 429:
                # Line 73:  Increment the rate limit counter for stats.
                self.rate_limit_count += 1
                # Line 74:  If we have retries left, wait and try again with exponential backoff.
                if attempt < self.max_retries:
                    # Line 76:  Calculate backoff delay (base_delay * 2^attempt for exponential growth).
                    delay = self.retry_delay * (2**attempt)
                    # Line 77:  Actually sleep to simulate waiting (in production this is real time).
                    time.sleep(delay)
                    # Line 78:  Continue to next retry attempt.
                    continue
                # Line 80:  If no retries left, break out and return the error response.
                break
            # Line 82:  Check if the response indicates a server error (HTTP 5xx).
            elif response.status_code >= 500:
                # Line 84:  Increment the server error counter for stats.
                self.server_error_count += 1
                # Line 85:  If we have retries left, wait and try again.
                if attempt < self.max_retries:
                    # Line 87:  Calculate backoff delay for server errors.
                    delay = self.retry_delay * (2**attempt)
                    # Line 88:  Sleep before retrying.
                    time.sleep(delay)
                    # Line 89:  Continue to next retry attempt.
                    continue
                # Line 91:  No retries left, break out.
                break
            # Line 93:  If we got a success (200), mark it and stop retrying.
            elif response.status_code == 200:
                # Line 95:  Increment success counter.
                self.success_count += 1
                # Line 96:  Extract token usage from the response body if present.
                if response.body and "usage" in response.body:
                    # Line 98:  Add prompt tokens to running total.
                    self.total_prompt_tokens += response.body["usage"].get(
                        "prompt_tokens", 0
                    )
                    # Line 99:  Add completion tokens to running total.
                    self.total_completion_tokens += response.body["usage"].get(
                        "completion_tokens", 0
                    )
                # Line 100:  Mark as successful.
                success = True
                # Line 101:  Stop retrying, we got a good response.
                break
            # Line 103:  Any other status code (4xx client errors) - don't retry, just return.
            else:
                # Line 105:  Break out of retry loop for non-retryable errors.
                break

        # Line 108:  Create a WireEvent to record this interaction in our log.
        event = WireEvent(
            request=request, response=response, purpose=purpose, success=success
        )
        # Line 109:  Append the event to our list of all intercepted wire events.
        self.events.append(event)
        # Line 110:  Return the final response (whether success or failure).
        return response

    # Line 113:  Get aggregate statistics about all wire traffic seen by this interceptor.
    def get_stats(self) -> Dict[str, Any]:
        # Line 115:  Calculate average latency from all successful responses.
        latencies = [
            e.response.latency_ms
            for e in self.events
            if e.response and not e.response.is_error
        ]
        # Line 116:  Compute mean latency (0 if no successful calls).
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        # Line 117:  Compute max latency seen.
        max_latency = max(latencies) if latencies else 0.0
        # Line 118:  Build and return the stats dictionary.
        return {
            # Line 120:  Total number of wire events (including retries).
            "total_requests": len(self.events),
            # Line 121:  Number of successful (200) responses.
            "successful": self.success_count,
            # Line 122:  Number of rate-limited (429) responses encountered.
            "rate_limited": self.rate_limit_count,
            # Line 123:  Number of server error (5xx) responses encountered.
            "server_errors": self.server_error_count,
            # Line 124:  Total prompt tokens consumed.
            "total_prompt_tokens": self.total_prompt_tokens,
            # Line 125:  Total completion tokens generated.
            "total_completion_tokens": self.total_completion_tokens,
            # Line 126:  Average latency in milliseconds.
            "avg_latency_ms": round(avg_latency, 2),
            # Line 127:  Maximum latency in milliseconds.
            "max_latency_ms": round(max_latency, 2),
        }

    # Line 130:  Format a single WireEvent as a human-readable wire dump string.
    @staticmethod
    def format_event(event: WireEvent) -> str:
        # Line 132:  Start building the formatted output.
        lines = []
        # Line 133:  Add a separator and header with the request ID and purpose.
        lines.append(f"  ┌─ [{event.request.request_id}] {event.purpose}")
        # Line 134:  Format the request section.
        lines.append(f"  │  REQUEST → {event.request.method} {event.request.url}")
        # Line 135:  Add each header line with proper indentation.
        for hk, hv in event.request.headers.items():
            # Line 137:  Format each header as "Key: Value" on its own line.
            lines.append(f"  │    {hk}: {hv}")
        # Line 138:  Add the JSON body (truncated for readability if very long).
        body_str = json.dumps(event.request.body, indent=2)
        # Line 139:  If body is longer than 200 chars, truncate with ellipsis.
        if len(body_str) > 200:
            # Line 141:  Truncate and add indicator.
            body_str = body_str[:200] + "\n  │    ... (truncated)"
        # Line 143:  Add the body with indentation.
        for bline in body_str.split("\n"):
            # Line 145:  Prefix each body line with proper wire-dump indentation.
            lines.append(f"  │    {bline}")
        # Line 146:  If there is a response, format it too.
        if event.response:
            # Line 148:  Add the response status line.
            resp = event.response
            # Line 149:  Build status string with color hint (success or error).
            status_label = (
                "OK" if resp.status_code == 200 else f"ERROR ({resp.status_code})"
            )
            # Line 150:  Add response header line.
            lines.append(
                f"  │  RESPONSE ← {resp.status_code} {status_label}  [{resp.latency_ms:.1f}ms]"
            )
            # Line 151:  Add response body if available (truncated).
            if resp.body:
                # Line 153:  Serialize the response body to JSON.
                rbody_str = json.dumps(resp.body, indent=2)
                # Line 154:  Truncate if too long.
                if len(rbody_str) > 200:
                    # Line 156:  Add truncation indicator.
                    rbody_str = rbody_str[:200] + "\n  │    ... (truncated)"
                # Line 158:  Add each response body line.
                for rline in rbody_str.split("\n"):
                    # Line 160:  Prefix with wire-dump indentation.
                    lines.append(f"  │    {rline}")
        # Line 162:  Close the box.
        lines.append(f"  └─")
        # Line 163:  Join all lines into a single string and return.
        return "\n".join(lines)

    # Line 166:  Print the full wire dump for all intercepted events (for debugging/learning).
    def print_wire_dump(self):
        # Line 168:  Print a header indicating we're showing raw wire traffic.
        print("\n" + "═" * 70)
        # Line 169:  Title the wire dump section.
        print("  WIRE TRAFFIC DUMP (what actually goes over the network)")
        # Line 170:  Print another separator line.
        print("═" * 70)
        # Line 171:  Iterate through every captured event.
        for i, event in enumerate(self.events):
            # Line 173:  Format and print each event's wire details.
            print(Interceptor.format_event(event))
            # Line 174:  Add a blank line between events for readability.
            print()
        # Line 176:  Print the closing separator.
        print("═" * 70)
