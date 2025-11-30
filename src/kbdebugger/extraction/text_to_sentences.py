from pathlib import Path
import string
from kbdebugger.compat.langchain import Document

def extract_txt_sentences(data_path: str) -> list[Document]:
    p = Path(data_path)

    # Try UTF-8 first; 'utf-8-sig' handles BOM if present.
    with p.open("r", encoding="utf-8-sig") as file:
        data = file.read()

    sentences = [s.strip().rstrip(string.punctuation)
                 for s in data.splitlines() if s.strip()]

    documents = []
    for i, sentence in enumerate(sentences):
        # Create a LangChain Document for each sentence
        doc = Document(
                page_content=sentence,
                metadata={
                    'page_number': i, # so each line is a different page
                    'source': data_path # e.g., './data/DSA/DSA_knowledge.txt'
                }
            )
        documents.append(doc)
        
    return documents
