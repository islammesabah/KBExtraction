from langchain.prompts import PromptTemplate

import re
import json

from LLM_Access.model_access import get_response

# sentence examples
sentences_examples = [
    {
        "sentence":"Data Preprocessing is subclass of Data Science Task",
        "output":"""["Data Preprocessing is subclass of Data Science Task"]"""
    },
    {
        "sentence":"""Transparency Property of an →KI system that is explainable and comprehensible. In the context of this quality standard, "transparency" also includes documentation of the properties of the →KI system.""",
        "output":"""["Transparency is a property of KI system.", "Transparency is explainable.", "Transparency is comprehensible.", "Transparency includes documentation of properties of KI system."]"""
    },
    {
        "sentence":"""opacity
opaqueness:
Property of a system that appropriate information about the system is unavailable to relevant stakeholders.""",
        "output":"""["Opacity also called Opaqueness.", "Opacity is a Property of a system.", "Property of a system has characteristic Information unavailable to stakeholders."]"""
    },
    {
        "sentence":"""This requirement is closely linked with the principle of explicability and encompasses transparency of elements relevant to an AI system: the data, the system and the business models.""",
        "output":"""["Requirement is linked with principle of explicability.", "Requirement encompasses Transparency of elements.", "Transparency is relevant to AI system. 4-Elements include Data.", "Elements include System. 6-Elements include Business models."]"""
    },
]

def create_examples(sentence_examples):
    examples = ""
    for ex in sentences_examples:
        examples += f"""
sentence: "{ex["sentence"].replace('"', "")}"
{{
"qualities" : "{ex["output"]}"
}}
"""
    return examples


# Prompt for the LLM to extract qualities from sentences
prompt_template = """<s>[INST]you are a helpful assistant. You will help me extract key qualities and properties of an AI system based on the sentences provided to you.
Keep in mind that the qualities you extract should connect to each other, in a way that when somebody reads the qualities, they should be able to make a graph from your statements.
Avoid mentioning redundant expressions.
Start from the important qualities and move forward to more detailed or other qualities that are related to previous ones.

Your answer must be structured as a JSON string. Do not answer in any other way, e.g. as normal text. Here is the structure:
{{"qualities": [List qualities you extracted from the text goes HERE]}}

if you do not adhere to this structure, everything will fail.
Make sure to never use other information except the text provided to you. Only use the reference text given to you for extracting the qualities.
Do not hallucinate. This is very important.
Try to be concise and to the point, because you are going to extract only qualities.
Don't write ``` at the beginning or end of your answer.

Here are some examples:
[/INST]
{examples}
</s>
[INST]sentence:{user_query}[/INST]
"""

prompt = PromptTemplate.from_template(prompt_template)

simple_rag_chain = (
    prompt          # build the prompt
    | get_response  # llm for generation
)
# get_response(prompt)

def extract(query):
    query_clean = query.replace('"', '')
    user_query = f'"{query_clean}"'

    res = simple_rag_chain.invoke({
        "examples": create_examples(sentences_examples),
        "user_query": user_query
    })

    # extract json object
    match = re.search(r"\{[^{}]*?\}", res)
    if match:
        try:
            return json.loads(match.group())["qualities"]
        except:
            return [query]
    else:
        return [query]