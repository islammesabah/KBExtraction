# - BM25 (Okapi BM25) is a ranking algorithm commonly used in search engines. 
# It calculates the relevance of documents to a query based on:
#     - The frequency of query terms in the document.
#     - The importance of those terms (e.g., frequent terms like "the" are weighted lower).
#     - The length of the document (shorter documents are typically favored).
#     - BM25 is a lexical search algorithm, meaning it matches words in the query to words in the document.


from rank_bm25 import BM25Okapi
from kbdebugger.compat.langchain import BM25Retriever

class ScoredBM25Retriever:
    def __init__(self, docs, k= 4):
        self.docs = docs
        self.k = k
        
        # Create BM25Okapi instance for scoring
        self.bm25_scorer = BM25Okapi(corpus=[doc.page_content.split() for doc in docs])
        
    def get_relevant_documents_and_scores(self, query):
        tokenized_query = query.lower().split()
        scores = self.bm25_scorer.get_scores(tokenized_query)

        # Pair documents with their BM25 scores
        doc_scores = sorted(zip(self.docs, scores), key=lambda x: x[1], reverse=True)
        
        retrieved_docs=[]
        for doc, score in doc_scores[:self.k]:
            doc.metadata["bm25_score"] = score
            retrieved_docs.append(doc)

        return retrieved_docs


def build_retriever(docs, k= 4):
    # for run call .invoke() on returned Object
    return BM25Retriever.from_documents(
                        docs,
                        k=k
                    )
    