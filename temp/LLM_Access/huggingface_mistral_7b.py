from langchain_huggingface import HuggingFaceEndpoint
import os
from dotenv import load_dotenv

# load the environment variables
load_dotenv(override=True)
HF_API_TOKEN = os.getenv("HF_API_TOKEN")

# define huggingface generation endpoint
hf_llm = HuggingFaceEndpoint(
    repo_id="mistralai/Mistral-7B-Instruct-v0.3", # Model Name
    task="text-generation",                       # task as generating a text response
    max_new_tokens=150,                           # maximum numbers of generated tokens
    do_sample=False,                              # disables sampling
    huggingfacehub_api_token=HF_API_TOKEN         # 🤗 huggingface API token
)


hf_llm.invoke("what is the capital of France?")
