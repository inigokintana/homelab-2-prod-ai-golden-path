import asyncio
import json
from dapr.clients import DaprClient
import time

def perform_selects():
    with DaprClient() as d:
        sql_binding = "pgdb-dvdrental"

        sqlCmd = ('select title, description from film where film_id=(SELECT FLOOR(RANDOM()*(1000 - 1 + 1)) + 1);')
        payload = {'sql': sqlCmd}

        # print(sqlCmd, flush=True)

        try:
        # Select using Dapr output binding via HTTP Post
            resp = d.invoke_binding(binding_name=sql_binding, operation='query',
                                     binding_metadata=payload)
            # print(resp, flush=True)
            result = resp.json()
            # print("Selected DB result:", result, flush=True)
            # print("-----------------", flush=True)
            return result
        except Exception as e:
             print(e, flush=True)
             raise SystemExit(e)

def invoke_ollama_via_dapr(prompt, model="llama3.2:1b"):
    """Invokes Ollama via Dapr service invocation."""

    with DaprClient() as d:
        # Define the payload to be sent to the Ollama API
        payload = {
            "model": model,
            "prompt": prompt,
            # "format": "json",
            "format": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string"
                            }
                        }
                    },
            "stream": False
        }

        # Define the Dapr service invocation endpoint
        # give us service discovery, retries and encripted communications
        resp = d.invoke_method(
            app_id='ollama-llm.ollama',
            method_name='api/generate',
            data=json.dumps(payload),
            http_verb='POST'
        )
    
        # Print the response
        # print(resp.content_type, flush=True)
        # print(resp.text(), flush=True)
        # print(str(resp.status_code), flush=True)

        time.sleep(2)
        return resp.text()

if __name__ == "__main__":
    """Main function to demonstrate Ollama invocation via Dapr."""
    while True:
        # Get a random film title and description from the database
        # and use it to generate a prompt for the LLM

        # 1 - Get a random film title and description from the database
        result=perform_selects()
        title_direct = result[0][0]
        description_direct = result[0][1]
        print("Selected DB result:", flush=True)
        print(f"- Film Title: {title_direct}")
        print(f"- Film Description: {description_direct}")
        
        # 2 - Use the description to generate a prompt for the LLM
        # Use the description to generate a prompt for the LLM
        prompt = "Please guess only the title of the following film description: " + description_direct
        # Calling Ollama LLM via Dapr
        llm_tittle_guess = invoke_ollama_via_dapr(prompt, model="llama3.2:1b")
        llm_response_dict = json.loads(llm_tittle_guess)

        # 3 - Compare the LLM guess with the actual title
        response_text = llm_response_dict["response"]
        # print(type(response_text), flush=True) -> str
        final_text_dict = json.loads(response_text)
        # print(type(final_text_dict), flush=True) -> dict
        print(" LLM response film title: " + final_text_dict["title"], flush=True)
        print("----------------------------------------------", flush=True)
        

        # 4 - Wait for a while before the next iteration
        time.sleep(10)
