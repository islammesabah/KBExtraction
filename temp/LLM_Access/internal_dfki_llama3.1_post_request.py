
import requests

def get_response(messages):
    # URL to send the POST request to
    url = "http://serv-3306.kl.dfki.de:8000/v1/chat/completions"

    # Data to send in the POST request
    data = {
        "model": "meta-llama-3.1-70b-instruct-fp8",
        "messages": messages,
        "max_tokens": 500,
    }

    # Send POST request
    response = requests.post(url, json=data)

    return response.json()["choices"][0]["message"]["content"]

messages = [    
        {
            "role": "system", 
            "content": "You are a helpful assistant."
        },    
        {
            "role": "user", 
            "content": "Hello, are you there?"
        } 
     ]

print(get_response(messages))
