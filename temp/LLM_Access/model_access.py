import os
from dotenv import load_dotenv
import requests

# load the environment variables
load_dotenv(override=True)
MODEL_SERVICE_URL = os.getenv("MODEL_SERVICE_URL", "http://serv-3306.kl.dfki.de:8000/v1/chat/completions")
MODEL_SERVICE_NAME = os.getenv("MODEL_SERVICE_NAME", "llama3.3-70b-instruct-fp8")
 
def get_response(prompt):
    # URL to send the POST request to
    url = MODEL_SERVICE_URL
 
    # Data to send in the POST request
    data = {
        "model": MODEL_SERVICE_NAME,
        "messages": [{
            "role": "user",
            "content": prompt if type(prompt) == str else prompt.text
        }],
        "max_tokens": 500,
    }
 
    # Send POST request
    response = requests.post(url, json=data)
    
    return response.json()["choices"][0]["message"]["content"]