import json
import time
from dapr.clients import DaprClient
# import os
import random
#import requests


#dapr_http_endpoint = os.getenv("DAPR_HTTP_ENDPOINT", "http://localhost:3500")

def invoke_ollama_via_dapr(prompt, model="llama3.2:1b"):
    """Invokes Ollama via Dapr service invocation."""

    with DaprClient() as d:
        # Define the payload to be sent to the Ollama API
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }

        # Define the Dapr service invocation endpoint
        resp = d.invoke_method(
            app_id='ollama-llm',
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

def main():
    """Main function to demonstrate Ollama invocation via Dapr."""

    animals = ['cat','dog','fish','bird','hamster','turtle','lizard','snake','frog','rabbit']
    while True:
        # Generate a random animal from the list
        animal = random.choice(animals)
        prompt = "Write a short poem about a " +  animal + " in a moderm style."
        response = invoke_ollama_via_dapr(prompt, model="llama3.2:1b")

        if response:
            print("Prompt:", flush=True)
            print(prompt, flush=True)
            print("Ollama Response:", flush=True)
            print(response, flush=True) 
            print("-----------------------------", flush=True)
        
        time.sleep(2)

if __name__ == "__main__":
    main()
