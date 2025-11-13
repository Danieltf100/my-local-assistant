"""
Function registry and execution service.

This module manages the registration and execution of callable functions
that the model can use.
"""

import logging
import inspect
from typing import Dict, Any, List, Optional, Callable

logger = logging.getLogger(__name__)


class FunctionRegistry:
    """
    Registry for managing available functions that the model can call.
    """
    
    def __init__(self):
        self.functions: Dict[str, Dict[str, Any]] = {}
        
    def register(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable
    ):
        """Register a new function"""
        self.functions[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "handler": handler
        }
        logger.info(f"Registered function: {name}")
        
    def get_function(self, name: str) -> Optional[Dict[str, Any]]:
        """Get function definition by name"""
        return self.functions.get(name)
        
    async def execute(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a function with given arguments (supports both sync and async functions)"""
        func = self.functions.get(name)
        if not func:
            return {"success": False, "error": f"Function '{name}' not found"}
            
        try:
            # Validate required parameters
            params_schema = func["parameters"]
            for param_name, param_def in params_schema.items():
                if param_def.get("required", False) and param_name not in arguments:
                    return {
                        "success": False,
                        "error": f"Missing required parameter: {param_name}"
                    }
            
            # Execute the function (handle both sync and async)
            handler = func["handler"]
            if inspect.iscoroutinefunction(handler):
                result = await handler(**arguments)
            else:
                result = handler(**arguments)
            
            return {"success": True, "result": result}
            
        except Exception as e:
            logger.error(f"Error executing function {name}: {str(e)}")
            return {"success": False, "error": str(e)}
            
    def get_all_functions(self) -> List[Dict[str, Any]]:
        """Get all registered functions"""
        return [
            {
                "name": func["name"],
                "description": func["description"],
                "parameters": func["parameters"]
            }
            for func in self.functions.values()
        ]
        
    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """Get functions in OpenAI tools format"""
        tools = []
        for func in self.functions.values():
            # Convert parameters to JSON schema format
            properties = {}
            required = []
            
            for param_name, param_def in func["parameters"].items():
                properties[param_name] = {
                    "type": param_def.get("type", "string"),
                    "description": param_def.get("description", "")
                }
                if "enum" in param_def:
                    properties[param_name]["enum"] = param_def["enum"]
                if param_def.get("required", False):
                    required.append(param_name)
            
            tools.append({
                "type": "function",
                "function": {
                    "name": func["name"],
                    "description": func["description"],
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required
                    }
                }
            })
        return tools

# Made with Bob
