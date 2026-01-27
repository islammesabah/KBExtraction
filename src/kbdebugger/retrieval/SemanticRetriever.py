# from kbdebugger.compat.langchain import Chroma
from kbdebugger.compat.langchain import Chroma
from .SentenceTransformerEmbeddings import SentenceTransformerEmbeddings

# def build_retriever(docs, k= 4):
#     # for run call .invoke() on returned Object

#     # Load the embeddings model
#     embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
#     # Most used and tried model
#     # embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-large-en-v1.5")

#     vector_store = Chroma(
#         collection_name="ADD_DATA", 
#         embedding_function=embeddings,
#     )

#     # Add documents and their embeddings to Chroma 
#     vector_store.add_documents(documents=docs)

#     retriever_chroma = vector_store.as_retriever(
#         search_type="mmr", search_kwargs={"k": k}
#     )
#     return retriever_chroma


def build_retriever(docs, k=4):
    # Load the embeddings model
    embeddings = SentenceTransformerEmbeddings(
        model_name="sentence-transformers/all-mpnet-base-v2"
    )

    vector_store = Chroma(
        collection_name="ADD_DATA",
        embedding_function=embeddings,
    )

    vector_store.add_documents(documents=docs)

    return vector_store.as_retriever(search_type="mmr", search_kwargs={"k": k})
