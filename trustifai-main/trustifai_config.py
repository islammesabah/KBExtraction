import warnings
warnings.simplefilter("ignore")
import configparser
import pprint

from terminal_interface import interface
from Requirement_Extraction.txt_sentences_extraction import txt_extraction
from Requirement_Extraction.pdf_sentences_extraction import create_sentences
from Requirement_Extraction.pdf_chunks import create_chunks
from Requirement_Extraction.sentence_decompose_old import extract as sentence_decompose
from Requirement_Extraction.chunk_decompose import extract as chunk_decompose

from Graph_Structuring.triplet_extraction import extract_triplets
from Graph_Structuring.neo4j_structure import create_relations, add_to_graph, query_graph

from Log.logs_dataframe import Logs

from tqdm import tqdm


def system_message(txt):
     print("\n##########>> SYSTEM <<##########")
     print(txt)
     print("################################\n")

def bulk_upload(data):
    relation_update = 0
    system_message("Bulk load the data to the graph.....")
    for doc in tqdm(data, desc="Decompose the Data", unit="item"):
        decompose_list = sentence_decompose(doc.page_content, config.get('LLM', 'requirement_extraction'))
        try:
            for sentence in decompose_list:
                edges = extract_triplets(sentence)
                for relation in create_relations(edges, doc):
                    logs.add_record_data(relation)
                    add_to_graph(relation)
                    relation_update += 1
        except:
            print(f"Not able to upload: {doc.page_content}")
            continue

    system_message(f"We add or update {relation_update} relations in your Graph Knowledge")

def decompose(inp):
    if config.get('General', 'extraction'):
        return sentence_decompose(inp, config.get('LLM', 'requirement_extraction'))
    else:
        return chunk_decompose(inp, config.get('LLM', 'requirement_extraction'))

def get_similar(data):    
    # build Retriever
    k = config.get('Retrieving', 'k')
    match config.get('Retrieving', 'approach'):
        case "Sparse Retrieval":
                from Retriever.BM25Retriever import build_retriever
                Retriever = build_retriever(data, k = k)
        case "Dense Retrieval":
                from Retriever.SemanticRetriever import build_retriever
                Retriever = build_retriever(data, k = k)
        case "Hybrid Retrieval":
                from Retriever.HybridRetriever import build_retriever
                Retriever = build_retriever(data, k = k)

    Cypher_query = config.get('Graph', 'cypher_query')    
    
    graph = query_graph(Cypher_query)

    print("---------------------")
    system_message(f"Information from the Graph to expand:")
    for i,sen in enumerate(graph):
        print(i," : ", sen["sentence"])
    print("---------------------\n")

    system_message("EXPAND SENTENCE ONE BY ONE:")
    for source in graph:
        print("################################################################")
        source = source["sentence"]
        system_message("Graph Information to expand:")
        print(source)
        
        relevant_docs = Retriever.invoke(source)
        print("---------------------")
        system_message(f"Relevant Information based on {config.get('Retrieving', 'approach')}:")
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
                    edges = extract_triplets(sentence)
                    print("Generated Edges",edges)
                    for relation in create_relations(edges, doc):
                        logs.add_record_data(relation)
                        system_message("Relation to be added to the graph:")
                        print(relation)
                        print("---------------------\n")
                        match interface(
                                "Would you like to upload previous relation to Graph Knowledge?", 
                                ["YES", "NO", "UPDATE"]
                            ):
                            case "YES":
                                add_to_graph(relation)
                                print("Added relation to graph")
                            case "NO":
                                print("Neglect the relation")
                            case "UPDATE":
                                source = input("Enter your updated source (empty if no update): ")
                                if source:
                                    relation["source"]["label"] = source
                                target = input("Enter your updated target (empty if no update): ")
                                if target:
                                    relation["target"]["label"] = target
                                relatn = input("Enter your updated relation (empty if no update): ")
                                if relatn:
                                    relation["edge"]["label"] = relatn
                                print("Your Updated Edge",relation)
                                match interface(
                                        "Would you like to upload the updated relation to Graph Knowledge?", 
                                        ["YES", "NO"]
                                    ):
                                    case "YES":
                                        add_to_graph(relation)
                                        logs.add_user_update(relation)
                                        print("Added relation to graph")
                                    case "NO":
                                        print("Neglect the relation")
                    print("&&&&&&&&&&&&&&&&&&&&&&&&")
            except:
                print(f"Not able to upload: {doc.page_content}")
                continue
        print("################################################################")



def main():
    data = None
    match config.get('Data', 'data_source'):
        case "DSA":
            data = txt_extraction("./Data/DSA/DSA_knowledge.txt")
        case "SDS":
            file = config.get('Data', 'data_file')
            match config.get('General', 'extraction'):
                case "Sentences":
                    data = create_sentences(file)
                case "Chunks":
                    data = create_chunks(file)

    system_message(f"The loaded data has {len(data)} records")
    
    if config.get('Data', 'data_source') == "DSA":
        if config.getboolean('General', 'bulk_load'):
            bulk_upload(data)
        else:
            get_similar(data)
    else:
        get_similar(data)
    
    
if __name__ == "__main__":
    logs = Logs()
    # Create a ConfigParser object
    config = configparser.ConfigParser()

    # Read the configuration file
    config.read('config.ini')

    # print run configuration
    print('Run setup: ')
    pprint.pprint({section: dict(config[section]) for section in config.sections()})
    
    main()