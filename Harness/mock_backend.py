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

    # Line 22:  Handle a WireRequest and return a WireResponse (simulates the API server).
    def handle(self, request: WireRequest) -> WireResponse:
        # Line 24:  Increment our internal request counter.
        self.request_count += 1
        # Line 25:  Simulate network + processing latency with a small sleep.
        latency = self.base_latency_ms + random.uniform(-30, 50)
        # Line 26:  Convert to seconds for time.sleep (which expects seconds).
        time.sleep(latency / 1000.0)

        # Line 28:  Check if we should simulate a rate limit response.
        if self.fail_mode == "rate_limit":
            # Line 30:  Return a 429 response immediately (no retry logic here, that's the interceptor's job).
            return WireResponse(
                # Line 32:  Correlate with the original request ID.
                request_id=request.request_id,
                # Line 33:  HTTP 429 = Too Many Requests.
                status_code=429,
                # Line 34:  Realistic rate-limit response headers.
                headers={"Retry-After": "1", "Content-Type": "application/json"},
                # Line 35:  JSON body explaining the rate limit.
                body={
                    "error": {
                        "message": "Rate limit exceeded. Try again in 1 second.",
                        "type": "rate_limit_error",
                    }
                },
                # Line 36:  Raw body as string (what you'd see with curl).
                raw_body=json.dumps({"error": {"message": "Rate limit exceeded."}}),
                # Line 37:  Latency for this failed request.
                latency_ms=latency,
                # Line 38:  Mark as error.
                is_error=True,
            )

        # Line 41:  Check if we should simulate a server error.
        if self.fail_mode == "server_error":
            # Line 43:  Return a 500 response.
            return WireResponse(
                # Line 45:  Correlate with the original request ID.
                request_id=request.request_id,
                # Line 46:  HTTP 500 = Internal Server Error.
                status_code=500,
                # Line 47:  Server error response headers.
                headers={"Content-Type": "application/json"},
                # Line 48:  JSON body with error details.
                body={
                    "error": {
                        "message": "Internal server error. Please try again.",
                        "type": "server_error",
                    }
                },
                # Line 49:  Raw body string.
                raw_body=json.dumps({"error": {"message": "Internal server error."}}),
                # Line 50:  Latency.
                latency_ms=latency,
                # Line 51:  Mark as error.
                is_error=True,
            )

        # Line 54:  Check if we're in "flaky" mode (succeed N times then fail).
        if self.fail_mode == "flaky" and self.request_count > self.fail_after:
            # Line 56:  Return a 503 Service Unavailable after the threshold.
            return WireResponse(
                # Line 58:  Correlate with request ID.
                request_id=request.request_id,
                # Line 59:  HTTP 503 = Service Unavailable.
                status_code=503,
                # Line 60:  Headers for service unavailable.
                headers={"Content-Type": "application/json"},
                # Line 61:  Body explaining the outage.
                body={
                    "error": {
                        "message": "Service temporarily unavailable.",
                        "type": "server_error",
                    }
                },
                # Line 62:  Raw body.
                raw_body=json.dumps(
                    {"error": {"message": "Service temporarily unavailable."}}
                ),
                # Line 63:  Latency.
                latency_ms=latency,
                # Line 64:  Mark as error.
                is_error=True,
            )

        # Line 67:  Normal success path - parse the request body to determine what to return.
        messages = request.body.get("messages", [])
        # Line 68:  Get the last user message content (this is what the "LM" responds to).
        last_user_msg = ""
        # Line 69:  Walk backwards through messages to find the last user message.
        for msg in reversed(messages):
            # Line 71:  If this message is from the user, capture its content and stop.
            if msg.get("role") == "user":
                # Line 73:  Store the content text.
                last_user_msg = msg.get("content", "")
                # Line 74:  Stop searching (we want the most recent user message).
                break

        # Line 76:  Determine if the user wants a tool call or a text response.
        # Line 77:  Check for math keywords that trigger tool calls.
        wants_tool = any(
            kw in last_user_msg.lower()
            for kw in ["add", "subtract", "calculate", "compute"]
        )

        # Line 79:  Build the appropriate response body based on intent.
        if wants_tool:
            # Line 81:  Extract numbers from the message for the tool call arguments.
            nums = [
                int(w)
                for w in last_user_msg.replace("and", " ").replace("plus", " ").split()
                if w.lstrip("-").isdigit()
            ]
            # Line 82:  Determine which tool to call based on keywords.
            if "subtract" in last_user_msg.lower():
                # Line 84:  Tool name for subtraction.
                tool_name = "subtract"
            # Line 85:  Default to addition for other math keywords.
            else:
                # Line 86:  Tool name for addition.
                tool_name = "add"
            # Line 87:  Build the tool call arguments (use first two numbers if available).
            args = {
                "a": nums[0] if len(nums) > 0 else 0,
                "b": nums[1] if len(nums) > 1 else 0,
            }
            # Line 88:  Construct the response body with a tool_call.
            response_body = {
                # Line 90:  The model identifier (echoed back for verification).
                "model": request.body.get("model", "toy-brain-v1"),
                # Line 91:  The choice containing the assistant's decision.
                "choices": [
                    {
                        # Line 93:  Index of this choice (always 0 for single-choice responses).
                        "index": 0,
                        # Line 94:  The message object with role and tool call info.
                        "message": {
                            # Line 96:  Role is always "assistant" in the response.
                            "role": "assistant",
                            # Line 97:  No text content when making a tool call.
                            "content": None,
                            # Line 98:  The tool call specification.
                            "tool_calls": [
                                {
                                    # Line 100:  Unique ID for this tool call instance.
                                    "id": f"call_{request.request_id}",
                                    # Line 101:  Type is always "function" in OpenAI-style APIs.
                                    "type": "function",
                                    # Line 102:  The function details.
                                    "function": {
                                        # Line 104:  Name of the tool to invoke.
                                        "name": tool_name,
                                        # Line 105:  JSON string of arguments (note: it's a STRING, not an object).
                                        "arguments": json.dumps(args),
                                    },
                                }
                            ],
                        },
                        # Line 109:  How the model decided to stop (tool_calls means it wants to use a tool).
                        "finish_reason": "tool_calls",
                    }
                ],
                # Line 112:  Token usage statistics (simulated based on message length).
                "usage": {
                    # Line 114:  Approximate prompt tokens (roughly 1 token per word across all messages).
                    "prompt_tokens": sum(
                        len(m.get("content", "").split()) for m in messages
                    )
                    * self.tokens_per_word,
                    # Line 115:  Approximate completion tokens (the tool call is short).
                    "completion_tokens": 12,
                    # Line 116:  Total = prompt + completion.
                    "total_tokens": sum(
                        len(m.get("content", "").split()) for m in messages
                    )
                    * self.tokens_per_word
                    + 12,
                },
            }
        # Line 119:  If no tool needed, return a text response.
        else:
            # Line 120:  Build a simple echo/acknowledgment text response.
            response_body = {
                # Line 122:  Model identifier.
                "model": request.body.get("model", "toy-brain-v1"),
                # Line 123:  Single choice with text content.
                "choices": [
                    {
                        # Line 125:  Choice index.
                        "index": 0,
                        # Line 126:  Message with text content (no tool call).
                        "message": {
                            # Line 128:  Role is assistant.
                            "role": "assistant",
                            # Line 129:  The actual text response.
                            "content": f"I processed your request: '{last_user_msg[:50]}'",
                            # Line 130:  No tool calls in a text response.
                            "tool_calls": None,
                        },
                        # Line 132:  Finish reason is "stop" (model finished naturally).
                        "finish_reason": "stop",
                    }
                ],
                # Line 135:  Token usage for text responses.
                "usage": {
                    # Line 137:  Prompt tokens estimate.
                    "prompt_tokens": sum(
                        len(m.get("content", "").split()) for m in messages
                    )
                    * self.tokens_per_word,
                    # Line 138:  Completion tokens (short response).
                    "completion_tokens": 8,
                    # Line 139:  Total.
                    "total_tokens": sum(
                        len(m.get("content", "").split()) for m in messages
                    )
                    * self.tokens_per_word
                    + 8,
                },
            }

        # Line 142:  Return a successful WireResponse with the constructed body.
        return WireResponse(
            # Line 144:  Correlate with request ID.
            request_id=request.request_id,
            # Line 145:  HTTP 200 = OK.
            status_code=200,
            # Line 146:  Realistic response headers from an API server.
            headers={
                # Line 148:  Content type is always JSON for LLM APIs.
                "Content-Type": "application/json",
                # Line 149:  Server identification (mimics real API responses).
                "X-Request-Id": request.request_id,
                # Line 150:  Rate limit info in headers (common pattern).
                "X-RateLimit-Remaining": "49",
            },
            # Line 152:  The parsed JSON body.
            body=response_body,
            # Line 153:  Raw string version of the body.
            raw_body=json.dumps(response_body),
            # Line 154:  Measured latency for this request.
            latency_ms=latency,
            # Line 155:  Not an error.
            is_error=False,
        )
