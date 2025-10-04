from sentence_decompose import extract
from pdf_sentences_extraction import create_sentences
from txt_sentences_extraction import txt_extraction
from pdf_chunks import create_chunks
querys = ["""Monitoring
Procedure in which deviations between observable actual states and the desired target states are detected
during the operation of an →KI system.""", """Fairness
Characteristic of an open process carried out by an →KI system if, in the course of this process, several
human individuals are treated in comparison with each other and this process is carried out in an open
process.
is free, from a legal point of view, from the mistreatment of a human individual on the basis of a legally
protected characteristic and also corresponds to the ideas of justice of the individuals to be named.""",
"""AI system must respect equally the moral worth and dignity of all human beings""",
"Model Deployment is subclass of Data Science Task"]

#query = "Natural Language Processing is subclass of Data Science Task"

# for query in querys:
#     decompose_list = extract(query)
#     print("=====================================")
#     print(query)
#     print("=====================================")
#     for i,sen in enumerate(decompose_list):
#         print(i," : ", sen)
#     print()

#print(create_sentences("./Data/SDS/20241015_MISSION_KI_Glossar_v1.0 en.pdf"))

print(create_chunks("./Data/SDS/20241015_MISSION_KI_Glossar_v1.0 en.pdf"))

#print(txt_extraction("./Data/DSA/DSA_knowledge.txt"))