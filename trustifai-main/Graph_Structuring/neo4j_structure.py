# from langchain_neo4j import Neo4jGraph
from langchain_community.graphs import Neo4jGraph
from dotenv import load_dotenv
import os

# load the environment variables
load_dotenv(override=True)

# Set up connection to graph instance using LangChain
kg = Neo4jGraph(
    url=os.getenv("NEO4J_URI"),
    username=os.getenv("NEO4J_USERNAME","neo4j"),
    password=os.getenv("NEO4J_PASSWORD","")
)

print(f"[TrustifAI] Connected to Neo4j at {os.getenv('NEO4J_URI')} as user '{os.getenv('NEO4J_USERNAME','neo4j')}'")

def create_relations(edge_object, sentence_doc):
    return [{
        'source': {
            'label': edge[0]
        },
        'target': {
            'label': edge[1]
        },
        'edge': {
            'label': edge[2],
            'properties': {
                'sentence': edge_object["sentence"],
                "original_sntence": sentence_doc.page_content, 
                **sentence_doc.metadata
            }

        },
    } for edge in edge_object["edges"]]

def get_graph(query: str) -> list[dict]:
    return kg.query(
        query
    )

def add_to_graph(relation):
    # relation = {
    #     'source': {
    #         'label': 'Monitoring'
    #     },
    #     'target': {
    #         'label': 'KI system'
    #     },
    #     'edge': {
    #         'label': 'is performed during operation of',
    #         'properties': {
    #             'sentence': 'Monitoring is performed during operation of KI system',
    #             'source': '20241015_MISSION_KI_Glossar_v1.0 en.pdf',
    #             'page_number': 1,
    #             'start_index': 0
    #         }

    #     },
    # }
    return kg.query(
          """
          MERGE(s:Node {label:$source_label})
          MERGE(t:Node {label:$target_label})
          WITH s,t
          CALL apoc.merge.relationship(s, $edge_label, 
                $properties
                , {}, t, {}) YIELD rel
          RETURN s,t,rel
          """, 
        params={
          'source_label': relation['source']['label'].strip().lower().replace(" ", "_"),
          'target_label': relation['target']['label'].strip().lower().replace(" ", "_"),
          'edge_label': relation['edge']['label'].strip().lower().replace(" ", "_"),
          'properties': relation['edge']['properties']
        }
    )
