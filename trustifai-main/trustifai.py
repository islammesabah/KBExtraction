import warnings
warnings.simplefilter("ignore")


from terminal_interface import interface
from Requirement_Extraction.txt_sentences_extraction import txt_extraction
from Requirement_Extraction.pdf_sentences_extraction import create_sentences
from Requirement_Extraction.pdf_chunks import create_chunks
from Requirement_Extraction.sentence_decompose import extract as sentence_decompose
from Requirement_Extraction.chunk_decompose import extract as chunk_decompose

from Graph_Structuring.relationship_extraction import create_item
from Graph_Structuring.neo4j_structure import create_relations, add_to_graph, get_graph

import glob
from tqdm import tqdm

# ENVIRONMENT VARIABLES
DATA_SOURCE = "DSA"
DATA_FILE = " ./Data/SDS/20241015_MISSION_KI_Glossar_v1.0 en.pdf"
EXTRACT_TYPE = "Sentences"
RETRIEVING_APPROACH = "Sparse Retrieval"
BULK_UPLOAD = True
 
def system_message(txt):
     print("\n##########>> SYSTEM <<##########")
     print(txt)
     print("################################\n")

def bulk_upload(data):
    relation_update = 0
    for doc in tqdm(data, desc="Decompose the Data", unit="item"):
        decompose_list = sentence_decompose(doc.page_content)
        try:
            for sentence in decompose_list:
                edges = create_item(sentence)
                for relation in create_relations(edges, doc):
                    print(relation)
                    add_to_graph(relation)
                    relation_update += 1
        except:
            print(f"Not able to upload: {doc.page_content}")
            continue

    system_message(f"We add or update {relation_update} relations in your Graph Knowledge")

def decompose(inp):
    if EXTRACT_TYPE == "Sentences":
        return sentence_decompose(inp)
    else:
        return chunk_decompose(inp)

def get_similar(data):
    BULK_UPLOAD = False
    global RETRIEVING_APPROACH
    # build Retriever
    match interface(
        "Which retrieving approach would you like to use?", 
        ["Dense Retrieval", "Sparse Retrieval", "Hybrid Retrieval"]
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

    Cypher_query = """ 
            MATCH (n)-[r:is]->(req:Node{label:"requirement"}) 
            RETURN DISTINCT r.sentence  as sentence
        """
    
    
    graph = get_graph(Cypher_query)

    for source in graph:
        print("################################################################")
        source = source["sentence"]
        system_message("Graph Information to expand:")
        print(source)
        relevant_docs = Retriever.invoke(source)
        # remoce the source from the relevant_docs
        relevant_docs = [doc for doc in relevant_docs if doc.page_content != source]
        print("---------------------")
        system_message(f"Relevant Information based on {RETRIEVING_APPROACH}:")
        for i,sen in enumerate(relevant_docs):
                print(i," : ", sen.page_content)
                print(sen.metadata)
        print("---------------------\n")
        for doc in relevant_docs:
            print("===========================================================")
            system_message("Add next Information to the Graph:")
            print(doc.page_content)
            decompose_list = decompose(doc.page_content)
            print("===========================================================")
            system_message("Atomic decomposed sentences:")
            for i,sen in enumerate(decompose_list):
                print(i," : ", sen)
            print("===========================================================")
            try:
                for sentence in decompose_list:
                    print("&&&&&&&&&&&&&&&&&&&&&&&&")
                    print("Sentence: ",sentence)
                    edges = create_item(sentence)
                    print("Generated Edge",edges)
                    for relation in create_relations(edges, doc):
                        match interface(
                                "Would you like to upload previous relation to Graph Knowledge?", 
                                ["YES", "NO"]
                            ):
                            case "YES":
                                add_to_graph(relation)
                                print("Added relation to graph")
                            case "NO":
                                print("Neglect the relation")
                    print("&&&&&&&&&&&&&&&&&&&&&&&&")
            except:
                print(f"Not able to upload: {doc.page_content}")
                continue
        print("################################################################")



def main():
    global DATA_SOURCE
    global DATA_FILE 
    global EXTRACT_TYPE 
    global BULK_UPLOAD 

    data = None
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