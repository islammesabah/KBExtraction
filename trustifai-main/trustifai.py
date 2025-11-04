from utils.warnings_config import install_warning_filters
install_warning_filters()


from terminal_interface import interface
from Requirement_Extraction.txt_sentences_extraction import txt_extraction
from Requirement_Extraction.pdf_sentences_extraction import create_sentences
from Requirement_Extraction.pdf_chunks import create_chunks
# from Requirement_Extraction.sentence_decompose_old import extract as sentence_decompose
from Requirement_Extraction.decomposer.sentence_decompose import build_sentence_decomposer
from Requirement_Extraction.decomposer.decompose import decompose, DecomposeMode
# from chunk_decompose import build_chunk_decomposer  # (we'll add similarly later)
# from Requirement_Extraction.chunk_decompose import extract as chunk_decompose

from Graph_Structuring.relationship_extraction import extract_triplets
from Graph_Structuring.neo4j_structure import map_extracted_triplets_to_graph_relations, query_graph, upsert_graph_relation
import glob
from tqdm import tqdm
from langchain_core.documents import Document
from LLM_Access.model_access import get_response

# ENVIRONMENT VARIABLES
DATA_SOURCE = "DSA"
DATA_FILE = " ./Data/SDS/20241015_MISSION_KI_Glossar_v1.0 en.pdf"
EXTRACT_TYPE = "Sentences"
RETRIEVING_APPROACH = "Sparse Retrieval"
BULK_UPLOAD = True
 
def system_message(txt: str) -> None:
     print("\n##########>> SYSTEM <<##########")
     print(txt)
     print("################################\n")

def bulk_upload(data):
    relation_update = 0
    for doc in tqdm(data, desc="Decompose the Data", unit="item"):
        # decompose_list = sentence_decompose(doc.page_content)
        doc_decomposed = decompose(
            text=doc.page_content,
            mode=DecomposeMode.SENTENCES,
        )
        try:
            for sentence in doc_decomposed:
                triplets = extract_triplets(sentence)
                for relation in map_extracted_triplets_to_graph_relations(triplets, doc):
                    print(relation)
                    upsert_graph_relation(relation)
                    relation_update += 1
        except:
            print(f"Not able to upload: {doc.page_content}")
            continue

    system_message(f"We add or update {relation_update} relations in your Graph Knowledge")

def get_similar(
    data: list[Document]
) -> None:
    """
    Get similar documents from the existing knowledge graph and add new relations based on user approval.
    Interactively asks the user for input on which retrieving approach to use and whether to upload new relations.
    Args:
        data (list): List of LangChain `Document` objects (produced earlier by create_sentences or create_chunks etc.). 
        to be used for retrieval and relation extraction.
        
        Assume data is a list of Document objects, each document can be as simple as one sentence or chunk.
        So we iterate over each document (sentence), use this sentence as a query and query the KB (Knowledge Graph) to get similar sentences that are already in the graph.
        
        Now say the KB result set returned 2 sentences.
        For each of these sentences, we now query our NEW DATA SOURCE (e.g., DSA knowledge.txt) using the retrieving approach (Dense, Sparse, Hybrid) to get relevant information.
    """
    BULK_UPLOAD = False # TODO: remove this line as it is not used
    global RETRIEVING_APPROACH
    # build Retriever
    match interface(
        message="Which retrieving approach would you like to use?", 
        options=["Dense Retrieval", "Sparse Retrieval", "Hybrid Retrieval"]
        ):
            case "Sparse Retrieval":
                from Retriever.BM25Retriever import build_retriever
                Retriever = build_retriever(data)
            case "Dense Retrieval":
                from Retriever.SemanticRetriever import build_retriever
                Retriever = build_retriever(data)
                RETRIEVING_APPROACH = "Dense Retrieval"
            case "Hybrid Retrieval":
                from Retriever.HybridRetriever import build_retriever
                Retriever = build_retriever(data)
                RETRIEVING_APPROACH = "Hybrid Retrieval"

    # Old:
    # Cypher_query = """ 
    #         MATCH (n)-[r:is]->(req:Node{label:"requirement"}) 
    #         RETURN DISTINCT r.sentence  as sentence
    #     """

    # New
    cypher_query = """ 
            MATCH (n)-[r:REL]->(req:Node{label:"requirement"}) 
            RETURN DISTINCT r.sentence as sentence
        """

    graph = query_graph(cypher_query)

    for source in graph:
        print("################################################################")
        source = source["sentence"] #e.g., "fairness is requirement"
        system_message("Graph Information to expand:")
        print(source)
        relevant_docs = Retriever.invoke(source) # type: ignore # retrieve relevant docs containing: "fairness is requirement"
        """
        # Example:
        relevant_docs = [
            Document(
                page_content="Equality is subclass of Fairness",
                metadata={"source": "DSA_knowledge.txt", "page_number": 3}
            ),
            Document(
                page_content="Human agency and oversight is a requirement",
                metadata={"source": "DSA_knowledge.txt", "page_number": 5}
            ),
        ]
        """
        # remove the source from the relevant_docs
        relevant_docs = [doc for doc in relevant_docs if doc.page_content != source]
        print("---------------------")
        system_message(f"Relevant Information based on the '{RETRIEVING_APPROACH}' retrieving approach:")
        for i,sen in enumerate(relevant_docs):
                print(i," : ", sen.page_content)
                print(sen.metadata)
        print("---------------------\n")
        for doc in relevant_docs:
            if not isinstance(doc, Document):
                continue
            
            print("===========================================================")
            system_message("Add next Information to the Graph:")
            print(doc.page_content)
            # decomposed_list = decompose(doc.page_content) # i.e., chunk the page_content
            doc_decomposed = decompose(
                text=doc.page_content,
                mode=DecomposeMode.SENTENCES,
                # sentence_decomposer=build_sentence_decomposer(),
                # chunk_decomposer=lambda s: [s],  # temporary: identity until we refactor chunk_decompose
            )
            """
            e.g., doc_decomposed = [
                "Human agency and oversight is a requirement.",
                "Equality is subclass of Fairness.",
            ]
            """
            # decompose_list is a list of chunks or sentences based on EXTRACT_TYPE
            print("===========================================================")
            system_message("Atomic decomposed sentences:")
            for i,sen in enumerate(doc_decomposed):
                print(i," : ", sen)
            print("===========================================================")
            try:
                for sentence in doc_decomposed:
                    print("&&&&&&&&&&&&&&&&&&&&&&&&")
                    print("Sentence: ",sentence)
                    extracted_triplets = extract_triplets(sentence)
                    """
                    e.g. 
                    extracted_triplets = {
                        'sentence': "Human agency and oversight is a requirement.",
                        'edges': [
                            ('Human agency', 'requirement', 'is'),
                            ('oversight', 'requirement', 'is')
                        ]
                    }
                    """
                    print(f"Extraction Result: {extracted_triplets}")
                    graph_relations = map_extracted_triplets_to_graph_relations(extracted_triplets, doc)
                    for relation in graph_relations:
                        match interface(
                                "Would you like to upload previous relation to Graph Knowledge?", 
                                ["YES", "NO"]
                            ):
                            case "YES":
                                upsert_graph_relation(relation)
                                print("[UPSERT] relation upserted to knowledge graph")
                            case "NO":
                                print("[INFO] relation neglected")
                    print("&&&&&&&&&&&&&&&&&&&&&&&&")
            except:
                print(f"Not able to upload: {doc.page_content}")
                continue
        print("################################################################")

def main():
    # module-level variables
    global DATA_SOURCE
    global DATA_FILE 
    global EXTRACT_TYPE 
    global BULK_UPLOAD 

    data: list | None = None
    match interface(
            "Which data source do you want to use?", 
            ["DSA", "SDS"]
        ):
        case "DSA":
            data = txt_extraction("./Data/DSA/DSA_knowledge.txt")
        case "SDS":
            DATA_SOURCE = "SDS"
            files_list = glob.glob("./Data/SDS/**/*.pdf", recursive=True)
            file = interface(
                "Which file do you want to use?", 
                files_list
            )
            DATA_FILE = file
            match interface(
                "Do you want to extract sentences or chunks?", 
                ["Sentences", "Chunks"]
            ):
                case "Sentences":
                    data = create_sentences(file)
                case "Chunks":
                    EXTRACT_TYPE = "Chunks"
                    data = create_chunks(file)
        
    if data is None:
        raise ValueError("No data loaded. Exiting.")

    system_message(f"The loaded data has {len(data)} records")
    
    if DATA_SOURCE == "DSA":
        match interface(
                    "Do you want the bulk upload to Graph Knowledge?", 
                    ["Yes", "No"]
        ):
            case "Yes":
                bulk_upload(data)
            case "No":
                get_similar(data)
    else:
        get_similar(data)
    
    
if __name__ == "__main__":
    main()