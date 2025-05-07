import requests
import json
import time
import os
import random

dapr_http_endpoint = os.getenv("DAPR_HTTP_ENDPOINT", "http://localhost:3500")
dapr_url = "{}/api/generate".format(dapr_http_endpoint)

def invoke_ollama_via_dapr(prompt, model="llama3.2:1b"):
    """Invokes Ollama via Dapr service invocation."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False  # Disable streaming for simplicity
    }

    try:
        response = requests.post(dapr_url, json=payload, headers = {"dapr-app-id": "ollama-llm"} )
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        result = response.json()
        return result["response"]
    except requests.exceptions.RequestException as e:
        print(f"Error invoking Ollama via Dapr: {e}", flush=True)
        return None
    except KeyError:
        print("Error: 'response' key not found in Ollama result.", flush=True)
        return None

def main():
    """Main function to demonstrate Ollama invocation via Dapr."""

    animals = ['cat','dog','fish','bird','hamster','turtle','lizard','snake','frog','rabbit']
    while True:
        # Generate a random animal from the list
        animal = random.choice(animals)
        prompt = "Write a short poem about a " +  animal + " in a moderm style."
        response = invoke_ollama_via_dapr(prompt)

        if response:
            print("Prompt:", flush=True)
            print(prompt, flush=True)
            print("Ollama Response:", flush=True)
            print(response, flush=True) 
            print("-----------------------------", flush=True)
        
        time.sleep(2)

if __name__ == "__main__":
    main()
