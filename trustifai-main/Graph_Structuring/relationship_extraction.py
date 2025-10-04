# For loading a PEFT model, we need to use a special object for CausalLM from PEFT
# instead of the regular HuggingFace object.
from peft import AutoPeftModelForCausalLM
from transformers import BitsAndBytesConfig
from transformers import AutoTokenizer
from huggingface_hub import login
from dotenv import load_dotenv

import torch
import os
import re
import json

# load the environment variables
load_dotenv(override=True)
HF_API_TOKEN = os.getenv("HF_API_TOKEN")

login(HF_API_TOKEN)

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,                     # Q = 4 bits
    #bnb_4bit_use_double_quant=True,        # double quantization, quantizing the quantization constants for saving an additional 0.4 bits per parameter
    bnb_4bit_quant_type="nf4",             # 4-bit NormalFloat Quantization (optimal for normal weights; enforces w ∈ [-1,1])
    bnb_4bit_compute_dtype=torch.bfloat16  # Dequantize to 16-bits before computations (as in the paper)
)

# Load the fine-tuned model
peft_model_path = "Graph_Structuring/fine-tuned-mistral"
tuned_model = AutoPeftModelForCausalLM.from_pretrained(
    peft_model_path,
    low_cpu_mem_usage = True,
    quantization_config=bnb_config  # Load with 4-bit quantization
)

# Load the tokenizer
tokenizer = AutoTokenizer.from_pretrained(peft_model_path)

# Set the padding token to be the same as the end-of-sequence token
tokenizer.pad_token = tokenizer.eos_token

# Specify that padding should be added to the right side of the sequences
tokenizer.padding_side = "right"

# Enable attention cache during inference
tuned_model.config.use_cache = True

# Define a function to build a prompt from a data example
def format_instruction(sentence, edges):
    return f"""
Extract relationships (edges) from the given sentences. Each relationship should be a triplet in the format `(Subject, Object, Relation)`, where:

1. **Subject**: The main entity initiating the action or relationship.
2. **Object**: The entity affected by or related to the Subject.
3. **Relation**: The action or relationship connecting the Subject and Object.

Return the results as a list of dictionaries. Each dictionary should have two keys:
- `"sentence"`: The original sentence.
- `"edges"`: A list of triplets representing the extracted edges.


Example:
Input Sentence: "Privacy and data governance ensures prevention of harm"
Output: {{'edges': [['Privacy', 'harm', 'ensures prevention of'], ['data governance', 'harm', 'ensures prevention of']], 'sentence': 'Privacy and data governance ensures prevention of harm'}}

Task:
Input Sentence: "{sentence.strip()}"
Output: {edges}
"""

# Define a function to generate a response
def create_item(sentnece):
    try:
        ex_inp = format_instruction(sentnece,"")
        inputs = tokenizer(ex_inp, return_tensors='pt')
        inputs = inputs.to("cuda")
        output_tokens = tuned_model.generate(
            inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            pad_token_id=tokenizer.pad_token_id,
            max_new_tokens=50,)[0]     # batch of tokens with one sequence
        res = tokenizer.decode(output_tokens, skip_special_tokens=True).replace(ex_inp,"")

        return json.loads(re.findall(r'{.*?}', res)[0].replace("\'","\""))

    except Exception as e:
        return {"error": str(e), 'message': "An error occurred. Please try again."}