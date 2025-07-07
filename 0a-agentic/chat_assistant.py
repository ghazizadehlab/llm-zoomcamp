import json

from IPython.display import display, HTML
import markdown

class Tools:
    def __init__(self):
        self.tools = {}
        self.functions = {}

    def add_tool(self, function, description):
        self.tools[function.__name__] = description
        self.functions[function.__name__] = function
    
    def get_tools(self):
        return list(self.tools.values())

    def function_call(self, tool_call):
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)

        f = self.functions[function_name]
        result = f(**arguments)

        return {
            "type": "function_call_output",
            "call_id": tool_call.id,
            "output": json.dumps(result, indent=2),
        }


def shorten(text, max_length=50):
    if len(text) <= max_length:
        return text

    return text[:max_length - 3] + "..."


class ChatInterface:
    def input(self):
        question = input("You:")
        return question
    
    def display(self, message):
        print(message)

    def display_function_call(self, tool_call, result):
        call_html = f"""
            <details>
            <summary>Function call: <tt>{tool_call.function.name}({shorten(tool_call.function.arguments)})</tt></summary>
            <div>
                <b>Call</b>
                <pre>{tool_call}</pre>
            </div>
            <div>
                <b>Output</b>
                <pre>{result['output']}</pre>
            </div>
            
            </details>
        """
        display(HTML(call_html))

    def display_response(self, message):
        response_html = markdown.markdown(message.content)
        html = f"""
            <div>
                <div><b>Assistant:</b></div>
                <div>{response_html}</div>
            </div>
        """
        display(HTML(html))



class ChatAssistant:
    def __init__(self, tools, developer_prompt, chat_interface, client):
        self.tools = tools
        self.developer_prompt = developer_prompt
        self.chat_interface = chat_interface
        self.client = client
    
    def gpt(self, chat_messages):
        return self.client.chat.completions.create(
            model='gpt-4o-mini',
            messages=chat_messages,
            tools=self.tools.get_tools(),
        )


    def run(self):
        chat_messages = [
            {"role": "developer", "content": self.developer_prompt},
        ]

        # Chat loop
        while True:
            question = self.chat_interface.input()
            if question.strip().lower() == 'stop':  
                self.chat_interface.display("Chat ended.")
                break

            message = {"role": "user", "content": question}
            chat_messages.append(message)

            while True:  # inner request loop
                response = self.gpt(chat_messages)

                has_messages = False
                
                # Get the message from the response
                message = response.choices[0].message
                
                # Add the assistant's message to chat history
                chat_messages.append({
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": message.tool_calls
                })

                # Handle tool calls if any
                if message.tool_calls:
                    for tool_call in message.tool_calls:
                        result = self.tools.function_call(tool_call)
                        chat_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result['output']
                        })
                        self.chat_interface.display_function_call(tool_call, result)
                else:
                    # Display the response
                    self.chat_interface.display_response(message)
                    has_messages = True

                if has_messages:
                    break
    


