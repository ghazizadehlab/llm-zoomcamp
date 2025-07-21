import json
import subprocess
import sys
import json

# Convert MCP tools format to OpenAI function format
def convert_tools_list(mcp_tools):
    """Convert MCP tools format to OpenAI function format"""
    openai_tools = []
    
    for tool in mcp_tools:
        openai_tool = {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        # Convert parameters
        for param in tool["parameters"]:
            param_name = param["name"]
            param_type = param["type"]
            
            # Map MCP types to JSON Schema types
            type_mapping = {
                "string": "string",
                "integer": "integer", 
                "number": "number",
                "float": "number",
                "boolean": "boolean"
            }
            
            openai_tool["function"]["parameters"]["properties"][param_name] = {
                "type": type_mapping.get(param_type.lower(), "string"),
                "description": param.get("description", "")
            }
            
            if param.get("required", True):
                openai_tool["function"]["parameters"]["required"].append(param_name)
                
        openai_tools.append(openai_tool)
        
    return openai_tools
      
# MCPClient class to interact with the MCP server
class MCPClient:
    def __init__(self, server_command):
        self.server_command = server_command
        self.process = None
        
    def start_server(self):
        """Start the MCP server process"""
        self.process = subprocess.Popen(
            self.server_command.split(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
    def send_request(self, request):
        """Send a JSON-RPC request to the server"""
        if not self.process:
            self.start_server()
            
        # Send the request
        request_str = json.dumps(request) + "\n"
        self.process.stdin.write(request_str)
        self.process.stdin.flush()
        
        # Read the response
        response = self.process.stdout.readline()
        return json.loads(response)
        
    def initialize(self):
        """Send the initialization request"""
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {"listChanged": True},
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        return self.send_request(init_request)
    
    def list_tools(self):
        """List available tools"""
        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/list",
            "params": {}
        }
        response = self.send_request(request)
        print('tools list response \n', response)
        if "error" in response:
            raise RuntimeError(f"Failed to list tools: {response['error']}")
            
        # Extract the tools from the response
        return response.get("result", {}).get("tools", [])
    
    def call_tool(self, tool_name, arguments):
        """Call a tool on the server"""
        request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        return self.send_request(request)
        
    def close(self):
        """Close the server process"""
        if self.process:
            self.process.terminate()
            self.process.wait()
            
# MCPTools class to convert MCP tools to OpenAI function format
class MCPTools:
    def __init__(self, mcp_client):
        self.mcp_client = mcp_client
        self.tools = None
    
    def get_tools_for_openai(self):
        if self.tools is None:
            try:
                mcp_tools = self.mcp_client.list_tools()
                self.tools = convert_tools_list(mcp_tools)
            except RuntimeError as e:
                print(f"Warning: Could not get tools from server: {e}")
                print("Using hardcoded tool definitions...")
                
        return self.tools

    def function_call(self, tool_call_response):
        function_name = tool_call_response.name
        arguments = json.loads(tool_call_response.arguments)

        result = self.mcp_client.call_tool(function_name, arguments)

        return {
            "type": "function_call_output",
            "call_id": tool_call_response.call_id,
            "output": json.dumps(result, indent=2),
        }     

# Usage example
if __name__ == "__main__":
    client = MCPClient("python weather_server.py")
    
    try:
        # Send initialization request
        response = client.initialize()
        print("Initialization response:", response)
        
        # List available tools
        tools_response = client.list_tools()
        print("Available tools:", tools_response)
        
        # Call the add tool
        result = client.call_tool("add", {"a": 5, "b": 3})
        print("Add result:", result)
        
    finally:
        client.close() 