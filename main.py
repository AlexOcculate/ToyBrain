# Line 1:  Import sys and os for path setup (allows running from any directory).
import sys, os

# Line 2:  Add the current directory to Python's module search path.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Line 5:  Import all Harness components needed for the demo.
from Harness.interceptor import Interceptor

# Line 6:  Import the mock backend (simulated API server).
from Harness.mock_backend import MockBackend

# Line 7:  Import the simulated LM helper.
from Harness.simulated_lm import SimulatedLM

# Line 8:  Import the tool registry factory.
from Harness.tools import create_default_registry

# Line 9:  Import the agent loop.
from Harness.agent_loop import AgentLoop

# Line 10:  Import the trace logger for colored output.
from Harness.trace_logger import TraceLogger, C


# Line 14:  Main demonstration function showing wire-level mechanics.
def main():
    # Line 16:  Create a trace logger for colored console output.
    tracer = TraceLogger()

    # Line 18:  Print the module title with styling.
    print(
        f"\n{C.BOLD}{C.CYAN}╔══════════════════════════════════════════════════════════════════╗{C.RESET}"
    )
    # Line 19:  Module name in the box.
    print(
        f"{C.BOLD}{C.CYAN}║   MODULE #3: TOYBRAIN - Wire-Level API Mechanics               ║{C.RESET}"
    )
    # Line 20:  Subtitle explaining what we're demonstrating.
    print(
        f"{C.BOLD}{C.CYAN}║   Every lm.generate() call is an HTTPS POST. Let's see it.     ║{C.RESET}"
    )
    # Line 21:  Close the box.
    print(
        f"{C.BOLD}{C.CYAN}╚══════════════════════════════════════════════════════════════════╝{C.RESET}\n"
    )

    # Line 23:  ─── SETUP PHASE ─────────────────────────────────────────────
    # Line 24:  Log that we're setting up components.
    tracer.loop("Setting up interceptor + mock backend + LM + tools...")

    # Line 26:  Create the MockBackend (simulates an API server with ~150ms latency).
    backend = MockBackend(fail_mode="none")
    # Line 27:  Create the Interceptor wrapping the backend (this is our "wire tap").
    interceptor = Interceptor(backend=backend, max_retries=3, retry_delay=0.1)
    # Line 28:  Create the SimulatedLM (builds requests, parses responses).
    lm = SimulatedLM(model_name="toy-brain-v1")
    # Line 29:  Create the tool registry with add and subtract tools.
    tools = create_default_registry()
    # Line 30:  Create the AgentLoop that ties everything together.
    agent = AgentLoop(interceptor=interceptor, lm=lm, tools=tools, max_iterations=5)

    # Line 32:  Log setup completion.
    tracer.success("All components wired. Interceptor is listening on the wire.")

    # Line 34:  ─── DEMO 1: Normal tool call (add 3 and 5) ──────────────────
    # Line 35:  Print section header.
    print(f"\n{C.BOLD}{'─' * 70}{C.RESET}")
    # Line 36:  Section title.
    print(f"{C.BOLD}  DEMO 1: Tool call (add 3 and 5){C.RESET}")
    # Line 37:  Another separator.
    print(f"{C.BOLD}{'─' * 70}{C.RESET}\n")

    # Line 39:  Run the agent with a math request that triggers a tool call.
    tracer.loop("User asks: 'add 3 and 5'")
    # Line 40:  Execute the agent loop (this will make wire calls internally).
    result1 = agent.run("Please add 3 and 5 for me")
    # Line 41:  Log the result.
    tracer.success(f"Agent answered: '{result1}'")
    # Line 42:  Print the result to console.
    print(f"\n  {C.GREEN}Result: {result1}{C.RESET}")

    # Line 44:  ─── DEMO 2: Text response (no tool needed) ──────────────────
    # Line 45:  Print section header.
    print(f"\n{C.BOLD}{'─' * 70}{C.RESET}")
    # Line 46:  Section title.
    print(f"{C.BOLD}  DEMO 2: Text response (no tool needed){C.RESET}")
    # Line 47:  Separator.
    print(f"{C.BOLD}{'─' * 70}{C.RESET}\n")

    # Line 49:  Run the agent with a non-math request (triggers text response).
    tracer.loop("User asks: 'hello there'")
    # Line 50:  Execute the agent loop.
    result2 = agent.run("hello there")
    # Line 51:  Log the result.
    tracer.success(f"Agent answered: '{result2}'")
    # Line 52:  Print the result.
    print(f"\n  {C.GREEN}Result: {result2}{C.RESET}")

    # Line 54:  ─── DEMO 3: Rate limit handling (HTTP 429) ──────────────────
    # Line 55:  Print section header.
    print(f"\n{C.BOLD}{'─' * 70}{C.RESET}")
    # Line 56:  Section title.
    print(
        f"{C.BOLD}  DEMO 3: Rate limit (HTTP 429) - interceptor retries automatically{C.RESET}"
    )
    # Line 57:  Separator.
    print(f"{C.BOLD}{'─' * 70}{C.RESET}\n")

    # Line 59:  Create a NEW backend that always returns 429 (simulates rate limiting).
    rate_limited_backend = MockBackend(fail_mode="rate_limit")
    # Line 60:  Create a new interceptor with the rate-limited backend.
    rl_interceptor = Interceptor(
        backend=rate_limited_backend, max_retries=2, retry_delay=0.1
    )
    # Line 61:  Create a new agent loop using the rate-limited interceptor.
    rl_agent = AgentLoop(
        interceptor=rl_interceptor, lm=lm, tools=tools, max_iterations=3
    )

    # Line 63:  Log that we're about to hit a rate-limited API.
    tracer.warning("Switching to rate-limited backend (always returns 429)...")
    # Line 64:  Run the agent - it should fail gracefully after exhausting retries.
    result3 = rl_agent.run("add 1 and 2")
    # Line 65:  Log the graceful failure.
    tracer.error(f"Agent reported error gracefully: '{result3}'")
    # Line 66:  Print the result (shows the error was handled, not crashed).
    print(f"\n  {C.RED}Result: {result3}{C.RESET}")
    # Line 67:  Show that retries happened.
    print(
        f"  {C.YELLOW}(Interceptor retried {rl_interceptor.max_retries} times before giving up){C.RESET}"
    )

    # Line 69:  ─── WIRE DUMP: Show what actually went over the wire ────────
    # Line 70:  Print section header.
    print(f"\n{C.BOLD}{'─' * 70}{C.RESET}")
    # Line 71:  Section title.
    print(f"{C.BOLD}  WIRE DUMP: Raw HTTP traffic captured by interceptor{C.RESET}")
    # Line 72:  Separator.
    print(f"{C.BOLD}{'─' * 70}{C.RESET}\n")

    # Line 74:  Print the full wire dump from the main interceptor (demos 1 & 2).
    tracer.wire("Printing all captured wire events...")
    # Line 75:  Call the interceptor's wire dump method.
    interceptor.print_wire_dump()

    # Line 77:  ─── STATS: Aggregate metrics from the wire ──────────────────
    # Line 78:  Print section header.
    print(f"\n{C.BOLD}{'─' * 70}{C.RESET}")
    # Line 79:  Section title.
    print(f"{C.BOLD}  WIRE STATISTICS (main interceptor){C.RESET}")
    # Line 80:  Separator.
    print(f"{C.BOLD}{'─' * 70}{C.RESET}\n")

    # Line 82:  Get and display aggregate stats.
    stats = interceptor.get_stats()
    # Line 83:  Print each stat with formatting.
    print(f"  {C.CYAN}Total requests:      {stats['total_requests']}{C.RESET}")
    # Line 84:  Successful calls.
    print(f"  {C.GREEN}Successful (200):    {stats['successful']}{C.RESET}")
    # Line 85:  Rate limited calls.
    print(f"  {C.YELLOW}Rate limited (429):  {stats['rate_limited']}{C.RESET}")
    # Line 86:  Server errors.
    print(f"  {C.RED}Server errors (5xx): {stats['server_errors']}{C.RESET}")
    # Line 87:  Token usage.
    print(f"  {C.CYAN}Prompt tokens:       {stats['total_prompt_tokens']}{C.RESET}")
    # Line 88:  Completion tokens.
    print(f"  {C.CYAN}Completion tokens:   {stats['total_completion_tokens']}{C.RESET}")
    # Line 89:  Average latency.
    print(f"  {C.CYAN}Avg latency:         {stats['avg_latency_ms']}ms{C.RESET}")
    # Line 90:  Max latency.
    print(f"  {C.CYAN}Max latency:         {stats['max_latency_ms']}ms{C.RESET}")

    # Line 92:  ─── TRACE REPORT: Full colored execution trace ──────────────
    # Line 93:  Print the full trace report.
    tracer.report()

    # Line 95:  Final summary message.
    print(f"\n{C.BOLD}  KEY INSIGHT:{C.RESET}")
    # Line 96:  Explain what was demonstrated.
    print(f"  {C.CYAN}lm.generate() is really an HTTPS POST.{C.RESET}")
    # Line 97:  Explain the interceptor's role.
    print(
        f"  {C.CYAN}The Interceptor sits on the boundary between your code and the model provider.{C.RESET}"
    )
    # Line 98:  Explain what you can observe.
    print(
        f"  {C.CYAN}You can see: headers, JSON body, status codes, token counts, latency.{C.RESET}\n"
    )


# Line 101:  Entry point guard - only run main() when executed directly (not imported).
if __name__ == "__main__":
    # Line 103:  Call the main demonstration function.
    main()
