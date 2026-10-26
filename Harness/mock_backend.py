# Line 1:  Import time to simulate network latency in the mock backend.
import time

# Line 2:  Import json for constructing realistic JSON response bodies.
import json

# Line 3:  Import random to add slight variation to simulated latency.
import random

# Line 4:  Import typing for type hints.
from typing import Dict, Any, Optional

# Line 7:  Import WireRequest and WireResponse from the interceptor module (same package).
from .interceptor import WireRequest, WireResponse


# Line 11:  MockBackend simulates an LLM API server without any real network calls.
class MockBackend:
    # Line 13:  Constructor allows configuring failure modes for testing.
    def __init__(self, fail_mode: str = "none", fail_after: int = 0):
        # Line 15:  Store the failure mode: "none", "rate_limit", "server_error", "flaky".
        self.fail_mode = fail_mode
        # Line 16:  Number of successful responses before triggering the failure (for "flaky" mode).
        self.fail_after = fail_after
        # Line 17:  Counter tracking how many requests we've handled so far.
        self.request_count: int = 0
        # Line 18:  Base simulated latency in milliseconds (mimics a real API round-trip).
        self.base_latency_ms: float = 150.0
        # Line 19:  Simulated token cost per "word" in the prompt (rough approximation).
        self.tokens_per_word: int = 1

    # Line 22:  Helper: safely count words in a message's content (handles None content).
    @staticmethod
    def _count_words(message: Dict[str, Any]) -> int:
        # Line 24:  Get content; if it's None or missing, treat as empty string.
        content = message.get("content") or ""
        # Line 25:  Return word count (split on whitespace).
        return len(content.split())

    # Line 28:  Handle a WireRequest and return a WireResponse (simulates the API server).
    def handle(self, request: WireRequest) -> WireResponse:
        # Line 30:  Increment our internal request counter.
        self.request_count += 1
        # Line 31:  Simulate network + processing latency with a small sleep.
        latency = self.base_latency_ms + random.uniform(-30, 50)
        # Line 32:  Convert to seconds for time.sleep (which expects seconds).
        time.sleep(latency / 1000.0)

        # Line 34:  Check if we should simulate a rate limit response.
        if self.fail_mode == "rate_limit":
            # Line 36:  Return a 429 response immediately (no retry logic here, that's the interceptor's job).
            return WireResponse(
                # Line 38:  Correlate with the original request ID.
                request_id=request.request_id,
                # Line 39:  HTTP 429 = Too Many Requests.
                status_code=429,
                # Line 40:  Realistic rate-limit response headers.
                headers={"Retry-After": "1", "Content-Type": "application/json"},
                # Line 41:  JSON body explaining the rate limit.
                body={
                    "error": {
                        "message": "Rate limit exceeded. Try again in 1 second.",
                        "type": "rate_limit_error",
                    }
                },
                # Line 42:  Raw body as string (what you'd see with curl).
                raw_body=json.dumps({"error": {"message": "Rate limit exceeded."}}),
                # Line 43:  Latency for this failed request.
                latency_ms=latency,
                # Line 44:  Mark as error.
                is_error=True,
            )

        # Line 47:  Check if we should simulate a server error.
        if self.fail_mode == "server_error":
            # Line 49:  Return a 500 response.
            return WireResponse(
                # Line 51:  Correlate with the original request ID.
                request_id=request.request_id,
                # Line 52:  HTTP 500 = Internal Server Error.
                status_code=500,
                # Line 53:  Server error response headers.
                headers={"Content-Type": "application/json"},
                # Line 54:  JSON body with error details.
                body={
                    "error": {
                        "message": "Internal server error. Please try again.",
                        "type": "server_error",
                    }
                },
                # Line 55:  Raw body string.
                raw_body=json.dumps({"error": {"message": "Internal server error."}}),
                # Line 56:  Latency.
                latency_ms=latency,
                # Line 57:  Mark as error.
                is_error=True,
            )

        # Line 60:  Check if we're in "flaky" mode (succeed N times then fail).
        if self.fail_mode == "flaky" and self.request_count > self.fail_after:
            # Line 62:  Return a 503 Service Unavailable after the threshold.
            return WireResponse(
                # Line 64:  Correlate with request ID.
                request_id=request.request_id,
                # Line 65:  HTTP 503 = Service Unavailable.
                status_code=503,
                # Line 66:  Headers for service unavailable.
                headers={"Content-Type": "application/json"},
                # Line 67:  Body explaining the outage.
                body={
                    "error": {
                        "message": "Service temporarily unavailable.",
                        "type": "server_error",
                    }
                },
                # Line 68:  Raw body.
                raw_body=json.dumps(
                    {"error": {"message": "Service temporarily unavailable."}}
                ),
                # Line 69:  Latency.
                latency_ms=latency,
                # Line 70:  Mark as error.
                is_error=True,
            )

        # Line 73:  Normal success path - parse the request body to determine what to return.
        messages = request.body.get("messages", [])
        # Line 74:  Get the last user message content (this is what the "LM" responds to).
        last_user_msg = ""
        # Line 75:  Walk backwards through messages to find the last user message.
        for msg in reversed(messages):
            # Line 77:  If this message is from the user, capture its content and stop.
            if msg.get("role") == "user":
                # Line 79:  Store the content text (use 'or' to handle None).
                last_user_msg = msg.get("content") or ""
                # Line 80:  Stop searching (we want the most recent user message).
                break

        # Line 82:  Determine if the user wants a tool call or a text response.
        # Line 83:  Check for math keywords that trigger tool calls.
        wants_tool = any(
            kw in last_user_msg.lower()
            for kw in ["add", "subtract", "calculate", "compute"]
        )

        # Line 85:  Build the appropriate response body based on intent.
        if wants_tool:
            # Line 87:  Extract numbers from the message for the tool call arguments.
            nums = [
                int(w)
                for w in last_user_msg.replace("and", " ").replace("plus", " ").split()
                if w.lstrip("-").isdigit()
            ]
            # Line 88:  Determine which tool to call based on keywords.
            if "subtract" in last_user_msg.lower():
                # Line 90:  Tool name for subtraction.
                tool_name = "subtract"
            # Line 91:  Default to addition for other math keywords.
            else:
                # Line 92:  Tool name for addition.
                tool_name = "add"
            # Line 93:  Build the tool call arguments (use first two numbers if available).
            args = {
                "a": nums[0] if len(nums) > 0 else 0,
                "b": nums[1] if len(nums) > 1 else 0,
            }
            # Line 94:  Calculate prompt token count safely (handles None content in tool messages).
            prompt_tokens = (
                sum(self._count_words(m) for m in messages) * self.tokens_per_word
            )
            # Line 95:  Construct the response body with a tool_call.
            response_body = {
                # Line 97:  The model identifier (echoed back for verification).
                "model": request.body.get("model", "toy-brain-v1"),
                # Line 98:  The choice containing the assistant's decision.
                "choices": [
                    {
                        # Line 100:  Index of this choice (always 0 for single-choice responses).
                        "index": 0,
                        # Line 101:  The message object with role and tool call info.
                        "message": {
                            # Line 103:  Role is always "assistant" in the response.
                            "role": "assistant",
                            # Line 104:  No text content when making a tool call.
                            "content": None,
                            # Line 105:  The tool call specification.
                            "tool_calls": [
                                {
                                    # Line 107:  Unique ID for this tool call instance.
                                    "id": f"call_{request.request_id}",
                                    # Line 108:  Type is always "function" in OpenAI-style APIs.
                                    "type": "function",
                                    # Line 109:  The function details.
                                    "function": {
                                        # Line 111:  Name of the tool to invoke.
                                        "name": tool_name,
                                        # Line 112:  JSON string of arguments (note: it's a STRING, not an object).
                                        "arguments": json.dumps(args),
                                    },
                                }
                            ],
                        },
                        # Line 116:  How the model decided to stop (tool_calls means it wants to use a tool).
                        "finish_reason": "tool_calls",
                    }
                ],
                # Line 119:  Token usage statistics (simulated based on message length).
                "usage": {
                    # Line 121:  Prompt tokens (using safe _count_words helper).
                    "prompt_tokens": prompt_tokens,
                    # Line 122:  Approximate completion tokens (the tool call is short).
                    "completion_tokens": 12,
                    # Line 123:  Total = prompt + completion.
                    "total_tokens": prompt_tokens + 12,
                },
            }
        # Line 126:  If no tool needed, return a text response.
        else:
            # Line 127:  Calculate prompt token count safely (handles None content in tool messages).
            prompt_tokens = (
                sum(self._count_words(m) for m in messages) * self.tokens_per_word
            )
            # Line 128:  Build a simple echo/acknowledgment text response.
            response_body = {
                # Line 130:  Model identifier.
                "model": request.body.get("model", "toy-brain-v1"),
                # Line 131:  Single choice with text content.
                "choices": [
                    {
                        # Line 133:  Choice index.
                        "index": 0,
                        # Line 134:  Message with text content (no tool call).
                        "message": {
                            # Line 136:  Role is assistant.
                            "role": "assistant",
                            # Line 137:  The actual text response.
                            "content": f"I processed your request: '{last_user_msg[:50]}'",
                            # Line 138:  No tool calls in a text response.
                            "tool_calls": None,
                        },
                        # Line 140:  Finish reason is "stop" (model finished naturally).
                        "finish_reason": "stop",
                    }
                ],
                # Line 143:  Token usage for text responses.
                "usage": {
                    # Line 145:  Prompt tokens estimate (using safe helper).
                    "prompt_tokens": prompt_tokens,
                    # Line 146:  Completion tokens (short response).
                    "completion_tokens": 8,
                    # Line 147:  Total.
                    "total_tokens": prompt_tokens + 8,
                },
            }

        # Line 150:  Return a successful WireResponse with the constructed body.
        return WireResponse(
            # Line 152:  Correlate with request ID.
            request_id=request.request_id,
            # Line 153:  HTTP 200 = OK.
            status_code=200,
            # Line 154:  Realistic response headers from an API server.
            headers={
                # Line 156:  Content type is always JSON for LLM APIs.
                "Content-Type": "application/json",
                # Line 157:  Server identification (mimics real API responses).
                "X-Request-Id": request.request_id,
                # Line 158:  Rate limit info in headers (common pattern).
                "X-RateLimit-Remaining": "49",
            },
            # Line 160:  The parsed JSON body.
            body=response_body,
            # Line 161:  Raw string version of the body.
            raw_body=json.dumps(response_body),
            # Line 162:  Measured latency for this request.
            latency_ms=latency,
            # Line 163:  Not an error.
            is_error=False,
        )
