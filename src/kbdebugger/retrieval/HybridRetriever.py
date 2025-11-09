# Reciprocal Rank Fusion -> Paper -> https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf
# https://python.langchain.com/docs/how_to/ensemble_retriever/


from retrieval.BM25Retriever import build_retriever as build_BM25Retriever
from retrieval.SemanticRetriever import build_retriever as build_SemanticRetriever
from kbdebugger.compat.langchain import EnsembleRetriever

def build_retriever(docs, alpha=0.5, k = 4):
    # for run call .invoke() on returned Object
    
    BM25Retriever = build_BM25Retriever(docs, k=k)
    SemanticRetriever = build_SemanticRetriever(docs, k=k)
    return EnsembleRetriever(
        retrievers=[BM25Retriever, SemanticRetriever], 
        weights=[alpha, 1-alpha]
    )
