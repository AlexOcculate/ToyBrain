# ToyBrain — Wire-Level API Mechanics (Interception)

**Module #3 in the TOYAGENTS curriculum.** See what really happens when your agent "talks to a model" — it's just an HTTP POST with a JSON body.

---

## Prerequisite

Understand **Module #2: ToyMCP** (tool discovery via protocol).

---

## What Is This?

Every time an AI agent calls a language model, something happens behind the scenes that most developers never see: an HTTP request goes out over the network, carrying headers and a JSON payload, and an HTTP response comes back with a status code, timing information, and token counts.

This module makes that invisible layer **visible**. It wraps every API call in an **Interceptor** — think of it as a wiretap on a phone line. You can see exactly what bytes left your machine, what came back, how long it took, and how many tokens were consumed. No real API key needed; a `MockBackend` simulates the server side.

**Intuitive analogy:** Imagine you're sending a letter to a friend. Normally you just drop it in a mailbox and wait. The Interceptor is like a postal inspector who copies every letter (both outgoing and incoming), stamps the time, counts the words, and notes whether the mail carrier got rejected at the door. You still get your reply — but now you have a complete record of the conversation at the delivery level.

---

## Folder Structure

```text
ToyBrain/
├── main.py                  # Entry point: runs 3 demos + wire dump + stats
├── test_adversarial.py      # 5 adversarial tests proving robustness
├── README.md                # This file
└── Harness/
    ├── __init__.py          # Package marker
    ├── interceptor.py       # The wiretap: logs every request/response
    ├── mock_backend.py      # Simulated API server (no real network)
    ├── live_backend.py      # Real HTTP calls via urllib (optional)
    ├── simulated_lm.py      # Builds requests, parses responses
    ├── tools.py             # Tool registry (add, subtract)
    ├── agent_loop.py        # The main loop: send → parse → act → repeat
    └── trace_logger.py      # ANSI-colored execution trace
```

---

## Dependencies

**External:** None. Zero packages beyond Python's standard library.

**Standard library modules used:**

| Module           | Purpose                                       |
| ---------------- | --------------------------------------------- |
| `json`           | Serialize/deserialize wire payloads           |
| `time`           | Measure latency, simulate network delay       |
| `uuid`           | Generate unique request IDs for tracing       |
| `random`         | Add realistic variation to simulated latency  |
| `urllib.request` | Real HTTP calls (LiveBackend only)            |
| `urllib.error`   | Handle HTTP errors gracefully                 |
| `dataclasses`    | Structured WireRequest / WireResponse objects |
| `typing`         | Type hints for readability                    |

**Internal import graph:**

```text
main.py
  └── Harness/agent_loop.py
        ├── Harness/interceptor.py
        │     └── (no internal deps)
        ├── Harness/simulated_lm.py
        │     └── (no internal deps)
        └── Harness/tools.py
              └── (no internal deps)

Harness/mock_backend.py
  └── Harness/interceptor.py   (imports WireRequest, WireResponse)

Harness/live_backend.py
  └── Harness/interceptor.py   (imports WireRequest, WireResponse)

test_adversarial.py
  ├── Harness/interceptor.py
  ├── Harness/mock_backend.py
  ├── Harness/simulated_lm.py
  ├── Harness/tools.py
  └── Harness/agent_loop.py
```

---

## Execution

```bash
# Run the main demonstration (3 scenarios + wire dump + stats)
python main.py

# Run the adversarial test suite (5 tests)
python test_adversarial.py
```

No setup, no `pip install`, no API key. Just Python 3.8+.

---

## Expected Output

Running `python main.py` produces:

```text
╔══════════════════════════════════════════════════════════════════╗
║   MODULE #3: TOYBRAIN - Wire-Level API Mechanics                 ║
║   Every lm.generate() call is an HTTPS POST. Let's see it.       ║
╚══════════════════════════════════════════════════════════════════╝

──────────────────────────────────────────────────────────────────────
  DEMO 1: Tool call (add 3 and 5)
──────────────────────────────────────────────────────────────────────

  Result: I processed your request: 'Please add 3 and 5 for me'

──────────────────────────────────────────────────────────────────────
  DEMO 2: Text response (no tool needed)
──────────────────────────────────────────────────────────────────────

  Result: I processed your request: 'hello there'

──────────────────────────────────────────────────────────────────────
  DEMO 3: Rate limit (HTTP 429) - interceptor retries automatically
──────────────────────────────────────────────────────────────────────

  Result: [ERROR] API returned status 429 after 2 retries.
  (Interceptor retried 2 times before giving up)

──────────────────────────────────────────────────────────────────────
  WIRE DUMP: Raw HTTP traffic captured by interceptor
──────────────────────────────────────────────────────────────────────

══════════════════════════════════════════════════════════════════════
  WIRE TRAFFIC DUMP (what actually goes over the network)
══════════════════════════════════════════════════════════════════════
  ┌─ [a3f2b1c9] Iteration 1: asking model for next action
  │  REQUEST → POST /chat/completions
  │    Content-Type: application/json
  │    X-API-Version: v1
  │    User-Agent: ToyBrain/1.0
  │    {
  │      "model": "toy-brain-v1",
  │      "messages": [ ... ],
  │      "temperature": 0.7,
  │      "max_tokens": 1024,
  │      "tools": [ ... ]
  │    }
  │  RESPONSE ← 200 OK  [148.3ms]
  │    {
  │      "model": "toy-brain-v1",
  │      "choices": [ ... tool_calls: add(3,5) ... ],
  │      "usage": { "prompt_tokens": 28, "completion_tokens": 12 }
  │    }
  └─

  (additional wire events for iterations 2 and 3 follow the same format)

══════════════════════════════════════════════════════════════════════

──────────────────────────────────────────────────────────────────────
  WIRE STATISTICS (main interceptor)
──────────────────────────────────────────────────────────────────────

  Total requests:      3
  Successful (200):    3
  Rate limited (429):  0
  Server errors (5xx): 0
  Prompt tokens:       28
  Completion tokens:   28
  Avg latency:         155.37ms
  Max latency:         162.7ms

══════════════════════════════════════════════════════════════════════
  EXECUTION TRACE
══════════════════════════════════════════════════════════════════════
  +0.00s  [LOOP]   Setting up interceptor + mock backend + LM + tools...
  +0.00s  [OK]     All components wired. Interceptor is listening on the wire.
  +0.00s  [LOOP]   User asks: 'add 3 and 5'
  +0.48s  [OK]     Agent answered: 'I processed your request: ...'
  ...
══════════════════════════════════════════════════════════════════════

  KEY INSIGHT:
  lm.generate() is really an HTTPS POST.
  The Interceptor sits on the boundary between your code and the model provider.
  You can see: headers, JSON body, status codes, token counts, latency.
```

Running `python test_adversarial.py` produces:

```text
  PASS  Broken LM / Chaotic output
  PASS  Hostile / Invalid input
  PASS  Tool execution failure
  PASS  Infinite loop / Max iterations
  PASS  HTTP 429 rate limit (interceptor)

  5/5 tests passed.
```

---

## Architecture Diagram

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                         main.py (entry point)                           │
│                                                                         │
│   Creates: MockBackend → Interceptor → AgentLoop                        │
│   Runs 3 demos, prints wire dump + stats                                │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      AgentLoop (agent_loop.py)                          │
│                                                                         │
│   1. Build messages list (system + user + history)                      │
│   2. Call interceptor.send(url, headers, body)                          │
│   3. Parse response → tool_call or text                                 │
│   4. If tool_call: execute tool, append result, loop again              │
│   5. If text: return as final answer                                     │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   Interceptor (interceptor.py)                          │
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────┐       │
│   │  • Constructs WireRequest (method, url, headers, body)      │       │
│   │  • Calls backend.handle(request)                            │       │
│   │  • Measures latency                                         │       │
│   │  • Retries on 429/5xx with exponential backoff              │       │
│   │  • Logs every WireEvent to self.events[]                    │       │
│   │  • Tracks: total tokens, rate limits, errors, latency       │       │
│   └─────────────────────────────────────────────────────────────┘       │
│                                                                         │
│   This is the "wiretap". Everything that crosses this boundary          │
│   is captured and logged.                                               │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              Backend (mock_backend.py  OR  live_backend.py)             │
│                                                                         │
│   MockBackend:                                                          │
│     • Simulates ~150ms network latency                                  │
│     • Returns JSON matching OpenAI API format                           │
│     • Configurable failure modes: none / rate_limit / server_error       │
│                                                                         │
│   LiveBackend (optional):                                               │
│     • Makes REAL HTTP POST via urllib.request                           │
│     • Works with any OpenAI-compatible endpoint                         │
│     • No external packages needed                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

**Key design decision:** The Interceptor is the ONLY component that knows about HTTP. The AgentLoop doesn't care whether it's talking to a mock or a real server. Swap the backend, everything else stays the same. This is the same "swap the brain, keep the body" principle from Module #0, applied at the network layer.

---

## State Machine Diagram

The agent loop in this module has a simple state machine:

```text
                    ┌──────────────┐
                    │   START      │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
              ┌────▶│  BUILD_REQ   │  Build messages + request body
              │     └──────┬───────┘
              │            │
              │            ▼
              │     ┌──────────────┐
              │     │ SEND_WIRE    │  interceptor.send() → backend.handle()
              │     └──────┬───────┘
              │            │
              │            ▼
              │     ┌──────────────┐     status != 200
              │     │ CHECK_RESP   │────────────────────┐
              │     └──────┬───────┘                    │
              │            │ status == 200              │
              │            ▼                            ▼
              │     ┌──────────────┐          ┌──────────────────┐
              │     │ PARSE_RESP   │          │ RETURN_ERROR     │
              │     └──────┬───────┘          │ "API returned    │
              │            │                  │  status X after  │
              │            ▼                  │  N retries"      │
              │     ┌──────────────┐          └──────────────────┘
              │     │ DECIDE       │
              │     └──┬───────┬───┘
              │        │       │
              │   tool_call   text
              │        │       │
              │        ▼       ▼
              │  ┌────────┐ ┌────────────┐
              │  │EXECUTE │ │  DONE      │
              │  │_TOOL   │ │ Return     │
              │  └───┬────┘ │ final text  │
              │      │      └────────────┘
              │      │
              │      ▼
              │  ┌────────────┐
              │  │APPEND_MSGS │  Add assistant + tool result to history
              │  └──────┬─────┘
              │         │
              └─────────┘  (loop back to BUILD_REQ)


Guardrail: if iteration count >= max_iterations → RETURN_ERROR("Max iterations reached")
```

**State descriptions:**

| State        | What happens                                                  | Exit condition                        |
| ------------ | ------------------------------------------------------------- | ------------------------------------- |
| START        | Initialize messages list with system + user prompt            | Always transitions to BUILD_REQ       |
| BUILD_REQ    | Assemble the JSON body (messages, tools, model, temperature)  | Always transitions to SEND_WIRE       |
| SEND_WIRE    | Interceptor sends request, handles retries, logs to wire dump | Returns a WireResponse                |
| CHECK_RESP   | Inspect HTTP status code                                      | 200 → PARSE_RESP; else → RETURN_ERROR |
| PARSE_RESP   | Extract tool_call or text from response body                  | Always transitions to DECIDE          |
| DECIDE       | Branch: is it a tool call or final text?                      | Routes to EXECUTE_TOOL or DONE        |
| EXECUTE_TOOL | Call the local Python function, get result string             | Always transitions to APPEND_MSGS     |
| APPEND_MSGS  | Add assistant message + tool result to conversation history   | Loops back to BUILD_REQ               |
| DONE         | Return the text content as the agent's final answer           | Terminal state                        |
| RETURN_ERROR | Return an error string (API failure or max iterations)        | Terminal state                        |

---

## File Reference

**`main.py`** — The demonstration script. Creates all components, runs three scenarios (normal tool call, text response, rate limit), then prints the full wire dump and aggregate statistics. This is what you run to *see* the concept in action.

**`Harness/interceptor.py`** — The core of this module. Defines `WireRequest`, `WireResponse`, and `WireEvent` dataclasses that model what actually travels over a network. The `Interceptor` class wraps any backend, adds retry logic with exponential backoff for transient errors (429, 5xx), tracks token usage and latency statistics, and records every event for later inspection via `print_wire_dump()`.

**`Harness/mock_backend.py`** — A fake API server that never touches the network. It sleeps for ~150ms to simulate latency, then returns a JSON response in OpenAI-compatible format. You can configure it to always fail (rate limit, server error) or be flaky (succeed N times then fail). This lets you study wire mechanics without spending real tokens.

**`Harness/live_backend.py`** — The "real" version. Uses `urllib.request` (stdlib only) to make an actual HTTPS POST to any OpenAI-compatible endpoint. Included for completeness and for those who want to point it at a local Ollama server or a real API key. Not used in the default demo.

**`Harness/simulated_lm.py`** — A helper class that knows how to *build* request bodies (messages, tools, model name) and *parse* response bodies (extract tool calls or text). It has no intelligence of its own — it's a translator between the agent's internal representation and the wire format.

**`Harness/tools.py`** — A registry that maps tool names to Python functions. Also stores the JSON Schema for each tool (this is what gets sent in the API request so the model knows what arguments to pass). The `execute()` method catches any exception from a tool and returns an error string, ensuring a crashing tool never crashes the agent.

**`Harness/agent_loop.py`** — The control loop. Maintains the conversation history, sends requests through the interceptor, parses responses, executes tools locally, and loops until it gets a text answer or hits the iteration cap. This is the "body" that works regardless of which backend (mock or live) is plugged in.

**`Harness/trace_logger.py`** — A colored console logger using ANSI escape codes (no external packages). Each component type gets its own color: wire events are cyan, loop progress is green, tool execution is yellow, errors are red. The `report()` method prints the full timestamped trace after execution.

**`test_adversarial.py`** — Five tests that prove the system survives hostile conditions: garbage responses from the "model", oversized/special-character inputs, a tool that raises an exception, a model that never stops calling tools (infinite loop), and persistent HTTP 429 rate limiting. All five must pass for the module to be considered robust.

---

## What This Teaches

| Concept                                     | Where to look                               | Key insight                                                                                                                                                                                           |
| ------------------------------------------- | ------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| An LLM API call is just HTTP POST           | `interceptor.py` → `WireRequest`            | There is no magic. It's a URL, some headers, and a JSON body. You could send it with `curl`.                                                                                                          |
| The wire format matters                     | `mock_backend.py` → response body structure | The model doesn't "think" in your language. It receives a specific JSON schema and returns a specific JSON schema. Getting the format wrong = error.                                                  |
| Status codes are your first line of defense | `interceptor.py` → retry logic              | 200 means success. 429 means "slow down". 5xx means "their problem, try again later". Your code must handle all three differently.                                                                    |
| Latency is real and measurable              | `interceptor.py` → `latency_ms`             | Every API call costs time. In a multi-step agent loop, latency adds up. This is why production systems use streaming.                                                                                 |
| Token counts are your cost meter            | `interceptor.py` → `total_prompt_tokens`    | You pay per token. The interceptor tracks this so you can see exactly what each conversation costs before it hits your credit card.                                                                   |
| The interceptor is a boundary               | `agent_loop.py` vs `interceptor.py`         | Your agent code never touches HTTP directly. It talks to the interceptor. The interceptor talks to the backend. This separation means you can swap mock for live with zero changes to the agent.      |
| Retries with backoff are essential          | `interceptor.py` → `send()` loop            | APIs rate-limit you. Servers have bad days. A single retry with exponential delay (1s, 2s, 4s) handles most transient failures without hammering the server.                                          |
| Tool results go back over the wire          | `agent_loop.py` → message history growth    | When a tool executes locally, its result is appended to the conversation and sent back to the model on the next API call. The model never "sees" your local execution — it only sees the text result. |

---

## Intuitive Summary

Think of this module like learning how a postal system works by watching a mail room:

- **Your agent** is the person writing the letter (building the JSON body).
- **The Interceptor** is the mail room clerk who stamps, copies, and logs every envelope.
- **The Backend** is the postal service that actually delivers it (mock = a fake delivery person in the next room; live = the real postal truck).
- **Status codes** are what happens at the recipient's door: "delivered" (200), "mailbox full, try later" (429), "house is on fire, come back tomorrow" (500).
- **Token counts** are like word count on a metered payphone — you know exactly how much you're spending.

Once you can see the wire, the "AI magic" becomes just... software engineering. And software engineering is debuggable.

---

## Parent Curriculum

This module is part of **TOYAGENTS** — a series of zero-dependency Python projects that teach agentic AI concepts one at a time.

Repository: https://github.com/AlexOcculate/TOYAGENTS

| #     | Module          | Concept                                            |
| ----- | --------------- | -------------------------------------------------- |
| 0     | ToyAgentNoBrain | Harness isolation from LLM                         |
| 1     | ToyA2A          | Message passing + delegation                       |
| 2     | ToyMCP          | Tool discovery via protocol (JSON-RPC)             |
| **3** | **ToyBrain**    | **Wire-level API mechanics (interception)**        |
| 4     | ToyPlanner      | Task decomposition (plan → execute → report)       |
| 5     | ToyEmbeddings   | Text to numeric vectors (similarity)               |
| 6     | ToyVectorDB     | Store and search by similarity                     |
| 7     | ToyRAG          | Retrieve, inject, grounded answer                  |
| 8     | ToySandBox      | Isolated tool execution + audit log                |
| 9     | ToyEvaluator    | Automated agent testing and scoring                |
| 10    | ToyCapstone     | Combine: MCP + Planner + RAG + SandBox + Evaluator |
