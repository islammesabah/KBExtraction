# Run: PYTHONPATH="." python Retriever/test.py 

from Requirement_Extraction.pdf_sentences_extraction import create_sentences


file = "Data/SDS/IEEE-P1522-2004.pdf"
data = create_sentences(file)
query = "Fairness is a Requirement"

from Retriever.BM25Retriever import build_retriever
BM25_Retriever = build_retriever(data)

relevant_docs = BM25_Retriever.invoke(query.lower())
print("---------------------")
print("Relevant Information based on BM25:\n")
for i,sen in enumerate(relevant_docs):
    print(i," : ", sen.page_content)
    print(sen.metadata)
print("---------------------\n")

from Retriever.SemanticRetriever import build_retriever
Sem_Retriever = build_retriever(data)

from Retriever.HybridRetriever import build_retriever
Retriever = build_retriever(data)




relevant_docs = Sem_Retriever.invoke(query.lower())
print("---------------------")
print("Relevant Information based on Semantic:\n")
for i,sen in enumerate(relevant_docs):
    print(i," : ", sen.page_content)
    print(sen.metadata)
print("---------------------\n")


relevant_docs = Retriever.invoke(query.lower())
print("---------------------")
print("Relevant Information based on Hybird:\n")
for i,sen in enumerate(relevant_docs):
    print(i," : ", sen.page_content)
    print(sen.metadata)
print("---------------------\n")