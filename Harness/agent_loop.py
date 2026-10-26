# Line 1:  Import typing for type hints.
from typing import List, Dict, Any, Optional

# Line 2:  Import json for message formatting.
import json

# Line 5:  Import Interceptor and WireResponse from the interceptor module.
from .interceptor import Interceptor, WireResponse

# Line 6:  Import SimulatedLM for building requests and parsing responses.
from .simulated_lm import SimulatedLM

# Line 7:  Import ToolRegistry for tool execution.
from .tools import ToolRegistry


# Line 11:  AgentLoop is the main control loop that orchestrates the agent's behavior.
class AgentLoop:
    # Line 13:  Constructor wires together all components.
    def __init__(
        self,
        interceptor: Interceptor,
        lm: SimulatedLM,
        tools: ToolRegistry,
        max_iterations: int = 5,
    ):
        # Line 15:  Store the interceptor (all API calls go through it).
        self.interceptor = interceptor
        # Line 16:  Store the LM helper (builds requests, parses responses).
        self.lm = lm
        # Line 17:  Store the tool registry (executes tools when model requests them).
        self.tools = tools
        # Line 18:  Maximum iterations to prevent infinite loops.
        self.max_iterations = max_iterations
        # Line 19:  The API endpoint URL that requests are sent to.
        self.api_url = "/chat/completions"
        # Line 20:  Default headers for every request (mimics real API client behavior).
        self.default_headers = {
            # Line 22:  Content type must be JSON.
            "Content-Type": "application/json",
            # Line 23:  API version header (common in LLM APIs).
            "X-API-Version": "v1",
            # Line 24:  User agent identifies the client (good practice for debugging).
            "User-Agent": "ToyBrain/1.0",
        }

    # Line 27:  Run the agent loop for a given user input, returning the final answer.
    def run(self, user_input: str) -> str:
        # Line 29:  Initialize the conversation message list (this grows with each turn).
        messages: List[Dict[str, str]] = []
        # Line 30:  Add the system prompt (tells the model what it can do).
        tool_names = self.tools.get_names()
        # Line 31:  Build and add the system message.
        messages.append(
            {"role": "system", "content": self.lm.build_system_prompt(tool_names)}
        )
        # Line 32:  Add the user's initial request.
        messages.append({"role": "user", "content": user_input})

        # Line 34:  Main loop - iterate until we get a text response or hit max iterations.
        for iteration in range(self.max_iterations):
            # Line 36:  Build the request body from current conversation state.
            body = self.lm.build_request_body(messages, tools=self.tools.get_schemas())

            # Line 38:  Send the request through the interceptor (this is where "the wire" happens).
            purpose = f"Iteration {iteration + 1}: asking model for next action"
            # Line 39:  The interceptor handles retries, logging, and returns the final response.
            response: WireResponse = self.interceptor.send(
                # Line 41:  The API endpoint path.
                url=self.api_url,
                # Line 42:  Headers for this request.
                headers=self.default_headers,
                # Line 43:  The JSON body with messages and tool definitions.
                body=body,
                # Line 44:  Purpose label for logging.
                purpose=purpose,
            )

            # Line 46:  Check if the response was an error (after all retries exhausted).
            if response.is_error or response.status_code != 200:
                # Line 48:  Return an error message indicating the API call failed.
                return f"[ERROR] API returned status {response.status_code} after {self.interceptor.max_retries} retries."

            # Line 50:  Parse the response to determine if it's a tool call or final text.
            parsed = self.lm.parse_response(response.body)

            # Line 52:  If the model wants to call a tool, execute it and continue the loop.
            if parsed["type"] == "tool_call":
                # Line 54:  Add the assistant's tool call message to the conversation history.
                messages.append(
                    {
                        # Line 56:  Role is assistant (the model made this decision).
                        "role": "assistant",
                        # Line 57:  No text content (it's a tool call, not text).
                        "content": None,
                        # Line 58:  Include the tool call in the message for context.
                        "tool_calls": [
                            {
                                # Line 60:  Tool call ID from the response.
                                "id": f"call_iter{iteration}",
                                # Line 61:  Type is function.
                                "type": "function",
                                # Line 62:  Function details.
                                "function": {
                                    # Line 64:  The tool name the model chose.
                                    "name": parsed["function_name"],
                                    # Line 65:  Arguments as JSON string (this is what goes in the message history).
                                    "arguments": json.dumps(parsed["arguments"]),
                                },
                            }
                        ],
                    }
                )

                # Line 69:  Execute the tool locally (this happens on OUR side, not the API's).
                tool_result = self.tools.execute(
                    parsed["function_name"], parsed["arguments"]
                )

                # Line 71:  Add the tool result as a new message in the conversation.
                messages.append(
                    {
                        # Line 73:  Role is "tool" (this is how OpenAI-style APIs represent tool results).
                        "role": "tool",
                        # Line 74:  The tool call ID that this result corresponds to.
                        "tool_call_id": f"call_iter{iteration}",
                        # Line 75:  The actual result string from executing the tool.
                        "content": tool_result,
                    }
                )

                # Line 77:  Continue the loop - the model will see the tool result and decide next step.
                continue

            # Line 80:  If the model returned text, that's our final answer.
            if parsed["type"] == "text":
                # Line 82:  Return the text content as the agent's final response.
                return parsed["content"]

            # Line 85:  Fallback (shouldn't reach here with well-formed responses).
            return "[ERROR] Unrecognized response type from model."

        # Line 88:  If we exhausted all iterations without getting a text response, report it.
        return f"[ERROR] Max iterations ({self.max_iterations}) reached without final answer."
