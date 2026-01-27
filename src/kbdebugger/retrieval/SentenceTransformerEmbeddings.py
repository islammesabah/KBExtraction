from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer

class SentenceTransformerEmbeddings(Embeddings):
    """
    Minimal LangChain Embeddings wrapper using sentence-transformers.
    Avoids the extra dependency: langchain-huggingface.
    """
    def __init__(self, model_name: str):
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, convert_to_numpy=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.model.encode([text], convert_to_numpy=True)[0].tolist()
    
