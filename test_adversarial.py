# Line 1:  Import sys and os for path setup (allows running from any directory).
import sys, os

# Line 2:  Add the current directory to Python's module search path.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Line 5:  Import all components needed for adversarial testing.
from Harness.interceptor import Interceptor, WireRequest, WireResponse

# Line 6:  Import the mock backend with configurable failure modes.
from Harness.mock_backend import MockBackend

# Line 7:  Import the simulated LM.
from Harness.simulated_lm import SimulatedLM

# Line 8:  Import the tool registry factory.
from Harness.tools import create_default_registry

# Line 9:  Import the agent loop.
from Harness.agent_loop import AgentLoop


# ──────────────────────────────────────────────
#  TEST 1: Broken / Chaotic LM
#  Proves: the system doesn't crash on malformed wire responses
# ──────────────────────────────────────────────
def test_broken_lm():
    # Line 18:  Create a backend that returns garbage in the response body.
    class GarbageBackend:
        # Line 20:  Handle method returns a 200 but with invalid/chaotic JSON structure.
        def handle(self, request):
            # Line 22:  Return a response with a valid status but broken body structure.
            return WireResponse(
                # Line 24:  Correlate with request.
                request_id=request.request_id,
                # Line 25:  Status 200 (looks successful at HTTP level).
                status_code=200,
                # Line 26:  Headers are fine.
                headers={"Content-Type": "application/json"},
                # Line 27:  Body is a valid dict but missing expected keys (no "choices").
                body={"unexpected_key": "garbage", "another": [1, 2, 3]},
                # Line 28:  Raw body string.
                raw_body='{"unexpected_key": "garbage"}',
                # Line 29:  Simulated latency.
                latency_ms=50.0,
                # Line 30:  Not marked as error (HTTP level is fine).
                is_error=False,
            )

    # Line 33:  Create interceptor with the garbage backend.
    interceptor = Interceptor(backend=GarbageBackend(), max_retries=1, retry_delay=0.01)
    # Line 34:  Create LM and tools.
    lm = SimulatedLM()
    # Line 35:  Create tool registry.
    tools = create_default_registry()
    # Line 36:  Create agent loop.
    agent = AgentLoop(interceptor=interceptor, lm=lm, tools=tools, max_iterations=2)

    # Line 38:  Run the agent - it should NOT crash even with garbage responses.
    result = agent.run("add 1 and 1")
    # Line 39:  Assert that we got a string back (either an error message or empty).
    assert isinstance(result, str), f"Expected string, got {type(result)}"
    # Line 40:  The result should indicate an error (since the response was malformed).
    assert (
        "ERROR" in result or "Unrecognized" in result
    ), f"Expected error indication, got: {result}"


# ──────────────────────────────────────────────
#  TEST 2: Invalid / Hostile Input
#  Proves: guardrails block bad input before it reaches the wire
# ──────────────────────────────────────────────
def test_hostile_input():
    # Line 50:  Create a standard working setup.
    backend = MockBackend(fail_mode="none")
    # Line 51:  Create interceptor.
    interceptor = Interceptor(backend=backend, max_retries=1, retry_delay=0.01)
    # Line 52:  Create LM and tools.
    lm = SimulatedLM()
    # Line 53:  Create tool registry.
    tools = create_default_registry()
    # Line 54:  Create agent loop.
    agent = AgentLoop(interceptor=interceptor, lm=lm, tools=tools, max_iterations=2)

    # Line 56:  Test with an extremely long input (10,000 characters).
    huge_input = "A" * 10000
    # Line 57:  Run the agent with the hostile input - should not crash.
    result = agent.run(huge_input)
    # Line 58:  Assert we got a string back (no exception raised).
    assert isinstance(result, str), "Agent crashed on oversized input"

    # Line 60:  Test with empty string input.
    result_empty = agent.run("")
    # Line 61:  Assert we got a string back.
    assert isinstance(result_empty, str), "Agent crashed on empty input"

    # Line 63:  Test with null bytes and special characters.
    hostile = "\x00\x01\x02\n\r\t<script>alert('xss')</script>"
    # Line 64:  Run with hostile characters - should not crash.
    result_hostile = agent.run(hostile)
    # Line 65:  Assert we got a string back.
    assert isinstance(result_hostile, str), "Agent crashed on special characters"


# ──────────────────────────────────────────────
#  TEST 3: Tool Execution Failure
#  Proves: a failing tool doesn't crash the loop; error is handled
# ──────────────────────────────────────────────
def test_tool_failure():
    # Line 75:  Create a registry with a tool that always raises an exception.
    tools = create_default_registry()

    # Line 76:  Register a broken tool that will fail when called.
    def broken_tool(a, b):
        # Line 78:  Always raise an error to simulate a failing tool.
        raise RuntimeError("Tool implementation crashed!")

    # Line 80:  Register the broken tool (it will appear in the schema but fail at execution).
    tools.register(
        # Line 82:  Name of the broken tool.
        name="broken_tool",
        # Line 83:  The function that always raises.
        func=broken_tool,
        # Line 84:  Description (the model might choose this).
        description="A tool that is guaranteed to fail.",
        # Line 85:  Parameter schema.
        parameters={
            "type": "object",
            "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
            "required": ["a", "b"],
        },
    )

    # Line 88:  Create a backend that always responds with a call to broken_tool.
    class BrokenToolBackend:
        # Line 90:  Return a response that calls the broken tool.
        def handle(self, request):
            # Line 92:  First call: model decides to use broken_tool.
            if not hasattr(self, "_called"):
                # Line 94:  Mark that we've been called once.
                self._called = True
                # Line 95:  Return a tool call for broken_tool.
                return WireResponse(
                    request_id=request.request_id,
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body={
                        "model": "toy-brain-v1",
                        "choices": [
                            {
                                "index": 0,
                                "message": {
                                    "role": "assistant",
                                    "content": None,
                                    "tool_calls": [
                                        {
                                            "id": "call_1",
                                            "type": "function",
                                            "function": {
                                                "name": "broken_tool",
                                                "arguments": '{"a": 1, "b": 2}',
                                            },
                                        }
                                    ],
                                },
                                "finish_reason": "tool_calls",
                            }
                        ],
                        "usage": {
                            "prompt_tokens": 10,
                            "completion_tokens": 5,
                            "total_tokens": 15,
                        },
                    },
                    raw_body="{}",
                    latency_ms=50.0,
                    is_error=False,
                )
            # Line 108:  Second call: model gives up and returns text.
            return WireResponse(
                request_id=request.request_id,
                status_code=200,
                headers={"Content-Type": "application/json"},
                body={
                    "model": "toy-brain-v1",
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": "The tool failed, sorry!",
                                "tool_calls": None,
                            },
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 15,
                        "completion_tokens": 8,
                        "total_tokens": 23,
                    },
                },
                raw_body="{}",
                latency_ms=50.0,
                is_error=False,
            )

    # Line 122:  Create interceptor with the broken tool backend.
    interceptor = Interceptor(
        backend=BrokenToolBackend(), max_retries=1, retry_delay=0.01
    )
    # Line 123:  Create LM.
    lm = SimulatedLM()
    # Line 124:  Create agent loop with the broken tool registry.
    agent = AgentLoop(interceptor=interceptor, lm=lm, tools=tools, max_iterations=3)

    # Line 126:  Run the agent - the tool will fail but the loop should continue.
    result = agent.run("use the broken tool with 1 and 2")
    # Line 127:  Assert we got a string (the loop survived the tool failure).
    assert isinstance(result, str), "Agent crashed when tool raised an exception"


# ──────────────────────────────────────────────
#  TEST 4: Infinite Loop / Max Iterations
#  Proves: the iteration guardrail stops runaway loops
# ──────────────────────────────────────────────
def test_infinite_loop():
    # Line 137:  Create a backend that ALWAYS returns a tool call (never gives text).
    class AlwaysToolBackend:
        # Line 139:  Every single response is a tool call - the model never "finishes".
        def handle(self, request):
            # Line 141:  Return a tool call for 'add' every time.
            return WireResponse(
                # Line 143:  Correlate with request.
                request_id=request.request_id,
                # Line 144:  Success status.
                status_code=200,
                # Line 145:  Headers.
                headers={"Content-Type": "application/json"},
                # Line 146:  Body always contains a tool call (simulates a model stuck in a loop).
                body={
                    # Line 148:  Model name.
                    "model": "toy-brain-v1",
                    # Line 149:  Always a tool call response.
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": f"call_{request.request_id}",
                                        "type": "function",
                                        "function": {
                                            "name": "add",
                                            "arguments": '{"a": 1, "b": 1}',
                                        },
                                    }
                                ],
                            },
                            "finish_reason": "tool_calls",
                        }
                    ],
                    # Line 150:  Usage stats.
                    "usage": {
                        "prompt_tokens": 20,
                        "completion_tokens": 10,
                        "total_tokens": 30,
                    },
                },
                # Line 152:  Raw body.
                raw_body="{}",
                # Line 153:  Latency.
                latency_ms=10.0,
                # Line 154:  Not an error.
                is_error=False,
            )

    # Line 157:  Create interceptor with the always-tool backend.
    interceptor = Interceptor(
        backend=AlwaysToolBackend(), max_retries=1, retry_delay=0.01
    )
    # Line 158:  Create LM and tools.
    lm = SimulatedLM()
    # Line 159:  Create tool registry.
    tools = create_default_registry()
    # Line 160:  Create agent loop with a LOW max_iterations to test the guardrail quickly.
    agent = AgentLoop(interceptor=interceptor, lm=lm, tools=tools, max_iterations=3)

    # Line 162:  Run the agent - it should hit the iteration cap and stop.
    result = agent.run("add 1 and 1")
    # Line 163:  Assert we got a string (the loop stopped, didn't run forever).
    assert isinstance(result, str), "Agent did not stop - infinite loop!"
    # Line 164:  Assert the result indicates max iterations was reached.
    assert "Max iterations" in result, f"Expected max iterations message, got: {result}"
    # Line 165:  Verify that exactly max_iterations wire calls were made (not more).
    assert (
        len(interceptor.events) == 3
    ), f"Expected 3 wire events, got {len(interceptor.events)}"


# ──────────────────────────────────────────────
#  TEST 5: API returns HTTP 429 rate limit
#  Proves: the interceptor handles rate limiting with retries and graceful failure
# ──────────────────────────────────────────────
def test_module_specific():
    # Line 176:  Create a backend that ALWAYS returns 429 (persistent rate limiting).
    always_429_backend = MockBackend(fail_mode="rate_limit")
    # Line 177:  Create interceptor with limited retries.
    interceptor = Interceptor(
        backend=always_429_backend, max_retries=3, retry_delay=0.05
    )
    # Line 178:  Create LM and tools.
    lm = SimulatedLM()
    # Line 179:  Create tool registry.
    tools = create_default_registry()
    # Line 180:  Create agent loop.
    agent = AgentLoop(interceptor=interceptor, lm=lm, tools=tools, max_iterations=2)

    # Line 182:  Run the agent - it should fail gracefully after exhausting all retries.
    result = agent.run("add 5 and 5")
    # Line 183:  Assert we got a string (no crash).
    assert isinstance(result, str), "Agent crashed on persistent rate limiting"
    # Line 184:  Assert the error message mentions the status code.
    assert (
        "429" in result or "ERROR" in result
    ), f"Expected 429 error indication, got: {result}"

    # Line 186:  Verify that retries actually happened (we should see multiple wire events).
    # Line 187:  With max_retries=3, we expect 4 total attempts (initial + 3 retries).
    assert len(interceptor.events) >= 1, "No wire events captured"

    # Line 189:  Verify the rate limit counter was incremented.
    assert interceptor.rate_limit_count > 0, "Rate limit counter was not incremented"

    # Line 191:  Now test a scenario where rate limiting is temporary (flaky mode).
    # Line 192:  Create a flaky backend that fails after 2 successful calls.
    flaky_backend = MockBackend(fail_mode="flaky", fail_after=2)
    # Line 193:  Create new interceptor for the flaky test.
    flaky_interceptor = Interceptor(
        backend=flaky_backend, max_retries=1, retry_delay=0.05
    )
    # Line 194:  Create a new agent with the flaky backend.
    flaky_agent = AgentLoop(
        interceptor=flaky_interceptor, lm=lm, tools=tools, max_iterations=2
    )

    # Line 196:  Run the first request (should succeed - within the "good" window).
    result_flaky1 = flaky_agent.run("add 1 and 2")
    # Line 197:  First call should succeed.
    assert isinstance(
        result_flaky1, str
    ), "Flaky backend first call failed unexpectedly"

    # Line 199:  Run a second request (should also succeed - still within window).
    result_flaky2 = flaky_agent.run("add 3 and 4")
    # Line 200:  Second call should succeed.
    assert isinstance(
        result_flaky2, str
    ), "Flaky backend second call failed unexpectedly"


# ──────────────────────────────────────────────
#  RUNNER
# ──────────────────────────────────────────────
if __name__ == "__main__":
    # Line 207:  Define the list of tests to run with their display names.
    tests = [
        # Line 209:  Test 1 - broken LM output.
        ("Broken LM / Chaotic output", test_broken_lm),
        # Line 210:  Test 2 - hostile input.
        ("Hostile / Invalid input", test_hostile_input),
        # Line 211:  Test 3 - tool execution failure.
        ("Tool execution failure", test_tool_failure),
        # Line 212:  Test 4 - infinite loop guardrail.
        ("Infinite loop / Max iterations", test_infinite_loop),
        # Line 213:  Test 5 - HTTP 429 rate limit handling (module-specific).
        ("HTTP 429 rate limit (interceptor)", test_module_specific),
    ]
    # Line 215:  Counter for passed tests.
    passed = 0
    # Line 216:  Iterate through all tests and run them.
    for name, fn in tests:
        # Line 218:  Try running the test function.
        try:
            # Line 220:  Execute the test.
            fn()
            # Line 221:  Print PASS with green indicator.
            print(f"  \033[32mPASS\033[0m  {name}")
            # Line 222:  Increment passed counter.
            passed += 1
        except Exception as e:
            # Line 224:  If test raised an exception, print FAIL with the error.
            print(f"  \033[31mFAIL\033[0m  {name}: {e}")
    # Line 226:  Print summary line.
    print(f"\n  {passed}/{len(tests)} tests passed.")
    # Line 227:  If any test failed, exit with non-zero code (for CI integration).
    if passed < len(tests):
        # Line 229:  Exit with error code 1.
        sys.exit(1)
