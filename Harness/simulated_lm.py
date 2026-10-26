# Line 1:  Import json for parsing tool call arguments from wire responses.
import json

# Line 2:  Import typing for type hints.
from typing import List, Dict, Any, Optional


# Line 5:  SimulatedLM is the "brain" that decides what to do based on conversation context.
# Line 6:  In this module, it doesn't make API calls itself - the AgentLoop does.
# Line 7:  Instead, it provides helper methods to interpret wire responses and build requests.
class SimulatedLM:
    # Line 9:  Constructor takes a model name for identification in wire traffic.
    def __init__(self, model_name: str = "toy-brain-v1"):
        # Line 11:  Store the model name (appears in request body and response).
        self.model_name = model_name
        # Line 12:  Temperature for generation (affects randomness - simulated here).
        self.temperature: float = 0.7
        # Line 13:  Maximum tokens to generate per response.
        self.max_tokens: int = 1024

    # Line 16:  Build the API request body that would be sent over the wire.
    def build_request_body(
        self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        # Line 18:  Start with the core fields every LLM API request needs.
        body: Dict[str, Any] = {
            # Line 20:  Which model to use (this is what the API routes to).
            "model": self.model_name,
            # Line 21:  The conversation messages in order.
            "messages": messages,
            # Line 22:  Temperature controls randomness (0=deterministic, 1=creative).
            "temperature": self.temperature,
            # Line 23:  Maximum tokens to generate (prevents runaway responses).
            "max_tokens": self.max_tokens,
        }
        # Line 25:  If tools are provided, include them in the request.
        if tools:
            # Line 27:  Add the tools array so the model knows what functions it can call.
            body["tools"] = tools
            # Line 28:  Tell the model it's allowed to use tools (auto = let it decide).
            body["tool_choice"] = "auto"
        # Line 29:  Return the complete request body ready for JSON serialization.
        return body

    # Line 32:  Parse a wire response body and extract the assistant's decision.
    def parse_response(self, response_body: Dict[str, Any]) -> Dict[str, Any]:
        # Line 34:  Get the first (and only) choice from the response.
        choices = response_body.get("choices", [])
        # Line 35:  If no choices, return an error indicator.
        if not choices:
            # Line 37:  Return empty result with error flag.
            return {
                "type": "error",
                "content": "No choices in response",
                "tool_call": None,
            }
        # Line 39:  Get the message from the first choice.
        message = choices[0].get("message", {})
        # Line 40:  Check if the model wants to call a tool.
        tool_calls = message.get("tool_calls")
        # Line 41:  If there are tool calls, extract the first one's details.
        if tool_calls:
            # Line 43:  Get the function name from the tool call.
            func_name = tool_calls[0].get("function", {}).get("name", "")
            # Line 44:  Get the arguments (they come as a JSON string, must parse).
            args_str = tool_calls[0].get("function", {}).get("arguments", "{}")
            # Line 45:  Parse the arguments string into a dict.
            try:
                # Line 47:  Convert JSON string to Python dict.
                args = json.loads(args_str)
            except (json.JSONDecodeError, TypeError):
                # Line 50:  If parsing fails, use empty dict as fallback.
                args = {}
            # Line 51:  Return the tool call decision.
            return {
                # Line 53:  Type indicates this is a tool call request.
                "type": "tool_call",
                # Line 54:  The function name to invoke.
                "function_name": func_name,
                # Line 55:  Parsed arguments for the function.
                "arguments": args,
                # Line 56:  No text content when calling a tool.
                "content": None,
            }
        # Line 59:  If no tool calls, this is a text response.
        else:
            # Line 61:  Return the text content as the final answer.
            return {
                # Line 63:  Type indicates this is a final text response.
                "type": "text",
                # Line 64:  The actual text content from the model.
                "content": message.get("content", ""),
                # Line 65:  No tool call.
                "tool_call": None,
            }

    # Line 68:  Build a system prompt that tells the model what tools are available.
    def build_system_prompt(self, tool_names: List[str]) -> str:
        # Line 70:  Create the system message content describing available capabilities.
        tools_desc = ", ".join(tool_names) if tool_names else "none"
        # Line 71:  Return a formatted system prompt.
        return f"You are a helpful assistant with access to these tools: {tools_desc}. Use them when asked to perform calculations or operations."
