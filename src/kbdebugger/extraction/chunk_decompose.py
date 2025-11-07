# from langchain.prompts import PromptTemplate
from langchain_core.prompts import PromptTemplate

import re
import json

from LLM_Access.model_access import get_response

sentences_examples = [
    {
        "chunk":"""behavior and/or functioning of this →AI system in principle and during operation and, if necessary, to
terminate it.
Monitoring
Procedure in which deviations between observable actual states and the desired target states are detected
during the operation of an →KI system.
Non-discrimination
Characteristic of an open process carried out by an →KI system if, in the course of this process, several
human individuals are treated in comparison with each other and this process is carried out in an open
process.
is legally free from the mistreatment of a human individual on the basis of a legally protected
characteristic.
User information""",
        "output":"""1-AI system has property functioning in principle and during operation. 2-Monitoring is deviations between observable actual states and desired target states. 3-Deviations occur during operation of an KI system. 4-Monitoring is a procedure for detecting deviations during operation (Optional, better to have). 5-Non-discrimination is a characteristic of an open process by an KI system. 6-Open process treats several human individuals in comparison with each other. 7-Non-discrimination ensures no mistreatment of a human individual. 8-Mistreatment is based on legally protected characteristics."""
    },
    {
        "chunk":"""characteristic.
User information
Characteristics of an →AI system with regard to the quality of information, interaction and operation by a
user, including knowledge of the involvement of AI, barriers, and the quality of the user experience.
freedom and with a view to preventing nudging.
Robustness
Ability of an →AI system to maintain its regular and usual behavior and functioning in the best possible
way even in the event of non-malicious, adverse, disruptive or faulty inputs or external influences.
to keep.
Traceability
Property of an →KI system with regard to the ability to record the consecutive sequence of all decisions""",
        "output":"""1-AI system has characteristic User information. 2-User information relates to quality of information, interaction and operation by a user. 3-AI system includes Knowledge of AI involvement. 4-AI system includes barriers. 5-AI system includes quality of the user experience. 6-AI system has ability Robustness. 7-Robustness allows regular and usual behavior in adverse conditions. 8-AI system maintains behavior even under faulty inputs or external influences. 9-AI system has property Traceability. 10-Traceability relates to recording consecutive sequence of all decisions."""
    },
    {
        "chunk":"""that enter or have entered an →KI system along the entire life cycle.
Transparency
Property of an →KI system that is explainable and comprehensible. In the context of this quality
standard, "transparency" also includes documentation of the properties of the →KI system.""",
        "output":"""1-Transparency is a property of KI system. 2-Transparency is explainable. 3-Transparency is comprehensible. 4-Transparency includes documentation of properties of the KI system."""
    }
]

def create_examples(chunk_examples):
    examples = ""
    for ex in chunk_examples:
        examples += f"""
chunk: "{ex["chunk"].replace('"', "")}"
{{
"qualities" : "{ex["output"]}"
}}
"""
    return examples


prompt_template = """<s>[INST]you are a helpful assistant. You will help me extract key qualities and properties of an AI system based on the short text provided to you.

Your answer must be structured as a JSON string. Do not answer in any other way, e.g. as normal text. Here is the structure:
{{"qualities": [Ordered qualities you extracted from the text goes HERE]}}
If you do not adhere to this structure everything will fail.

Some notes:
* Keep in mind that the qualities you extract should connect to each other, in a way that when somebody reads the qualities, he should be able to make a graph from your statements.
* Ignore the examples in the text. Do not extract any qualities from them.
* Start from the important qualities and move forward to more detailed or other qualities that are related to previous ones.
* Make sure to never use other information except the text provided to you. Only use the reference text given to you for extracting the qualities.
* Do not hallucinate. This is very important.
* Try to be consice and to the point, because you are going to extract only qualities.
* Only answer with one json structure, like mentioned, don't output multiple json structured strings.
* If the text doesn't provide specific AI system qualities, just leave the "qualities" data in the json output empty string. Refrain from any further explanation. The empty string is completely enough.
* Don't write long qualities. If it is more than 10 words, just break it up and create a new quality from it.
* If multiple instances/aspects of an idea is present in the text, split them up and make distinct qualities for each.
* Ignore the sentences that are talking about the "Glossary" and its attributes, but don't forget to include AI system qualities.
* Don't use double quotes in the extracted qualities, otherwise the json cannot be parsed.
* Don't use newline in the qualities ordered list, write the ordered list of qualities in JUST ONE LINE.

Here are some examples:
[/INST]
{examples}
</s>
[INST]text: {user_query}[/INST]
"""

prompt = PromptTemplate.from_template(prompt_template)

simple_rag_chain = (
    prompt                                   # build the prompt
    | get_response                           # llm for generation
)

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