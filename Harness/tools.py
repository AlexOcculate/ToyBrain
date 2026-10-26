# Line 1:  Import typing for type hints.
from typing import Dict, Any, List, Callable


# Line 4:  Define the tool registry that maps tool names to their implementations.
class ToolRegistry:
    # Line 6:  Constructor initializes an empty mapping of tool name -> callable.
    def __init__(self):
        # Line 8:  Dictionary mapping tool names to their Python function implementations.
        self._tools: Dict[str, Callable] = {}
        # Line 9:  List of tool schema definitions (for sending in API requests).
        self._schemas: List[Dict[str, Any]] = []

    # Line 12:  Register a tool with its implementation and JSON schema.
    def register(
        self, name: str, func: Callable, description: str, parameters: Dict[str, Any]
    ):
        # Line 14:  Store the callable so we can invoke it when the model requests it.
        self._tools[name] = func
        # Line 15:  Build the OpenAI-compatible tool schema for the API request.
        schema = {
            # Line 17:  Type is always "function" in the tools array.
            "type": "function",
            # Line 18:  The function definition with name, description, and parameter schema.
            "function": {
                # Line 20:  The tool's name (what the model will reference).
                "name": name,
                # Line 21:  Human-readable description (helps the model decide when to use it).
                "description": description,
                # Line 22:  JSON Schema for the parameters (tells the model what args to pass).
                "parameters": parameters,
            },
        }
        # Line 25:  Append the schema to our list (this gets sent in every API request).
        self._schemas.append(schema)

    # Line 28:  Get all tool schemas (to include in the API request body).
    def get_schemas(self) -> List[Dict[str, Any]]:
        # Line 30:  Return a copy of the schemas list.
        return list(self._schemas)

    # Line 33:  Execute a tool by name with given arguments.
    def execute(self, name: str, arguments: Dict[str, Any]) -> str:
        # Line 35:  Check if the tool exists in our registry.
        if name not in self._tools:
            # Line 37:  Return an error string (not an exception - the agent loop handles this).
            return f"Error: Unknown tool '{name}'"
        # Line 39:  Attempt to call the registered function with the provided arguments.
        try:
            # Line 41:  Invoke the tool function, unpacking arguments as keyword args.
            result = self._tools[name](**arguments)
            # Line 42:  Convert result to string (tool results go back as text in the next message).
            return str(result)
        except Exception as e:
            # Line 45:  Catch ANY exception from tool execution (TypeError, RuntimeError, etc.).
            # Line 46:  Return a formatted error string so the agent loop can feed it back to the model.
            # Line 47:  This is critical: a crashing tool must NOT crash the entire agent.
            return (
                f"Error: Tool '{name}' failed with exception: {type(e).__name__}: {e}"
            )

    # Line 50:  Get list of registered tool names.
    def get_names(self) -> List[str]:
        # Line 52:  Return list of all registered tool names.
        return list(self._tools.keys())


# Line 56:  Create and populate the default tool registry with math tools.
def create_default_registry() -> ToolRegistry:
    # Line 58:  Instantiate a new empty registry.
    registry = ToolRegistry()

    # Line 60:  Register the 'add' tool.
    def add(a: int, b: int) -> int:
        # Line 62:  Return the sum of two numbers.
        return a + b

    # Line 64:  Register add with its schema.
    registry.register(
        # Line 66:  Tool name as the model will reference it.
        name="add",
        # Line 67:  The actual Python function to call.
        func=add,
        # Line 68:  Description helps the model understand when to use this tool.
        description="Add two integers together and return the result.",
        # Line 69:  JSON Schema defining the expected parameters.
        parameters={
            # Line 71:  Parameter schema uses JSON Schema format.
            "type": "object",
            # Line 72:  Properties defines each parameter's name and type.
            "properties": {
                # Line 74:  First parameter 'a' is an integer.
                "a": {"type": "integer", "description": "First number"},
                # Line 75:  Second parameter 'b' is an integer.
                "b": {"type": "integer", "description": "Second number"},
            },
            # Line 77:  Both parameters are required (model must provide both).
            "required": ["a", "b"],
        },
    )

    # Line 81:  Register the 'subtract' tool.
    def subtract(a: int, b: int) -> int:
        # Line 83:  Return the difference (a minus b).
        return a - b

    # Line 85:  Register subtract with its schema.
    registry.register(
        # Line 87:  Tool name.
        name="subtract",
        # Line 88:  The function implementation.
        func=subtract,
        # Line 89:  Description for the model.
        description="Subtract the second integer from the first and return the result.",
        # Line 90:  Parameter schema (same structure as add).
        parameters={
            # Line 92:  Object type.
            "type": "object",
            # Line 93:  Define the two integer properties.
            "properties": {
                # Line 95:  First number to subtract from.
                "a": {"type": "integer", "description": "Number to subtract from"},
                # Line 96:  Second number to subtract.
                "b": {"type": "integer", "description": "Number to subtract"},
            },
            # Line 98:  Both required.
            "required": ["a", "b"],
        },
    )

    # Line 102:  Return the fully populated registry.
    return registry
