import string
from langchain.schema import Document

def txt_extraction(data_path: str) -> list[Document]:
    with open(data_path, "r") as file:
        data = file.read()
    sentences = [s.strip().rstrip(string.punctuation) for s in data.strip().split('\n') if s.strip()]

    documents = []
    for i, sentence in enumerate(sentences):
        doc = Document(
                page_content=sentence,
                metadata={
                    'page_number': i,
                    'source': data_path
                }
            )
        documents.append(doc)
        
    return documents
