# from relationship_extraction import create_item
from neo4j_structure import add_to_graph, get_graph

# query = """Monitoring is performed during operation of KI system"""

# res = create_item(query)
# print(res)
 
# relation = {
#         'source': {
#             'label': 'Video Analysis'
#         },
#         'target': {
#             'label': 'Data Science Task'
#         },
#         'edge': {
#             'label': 'is subclass of',
#             'properties': {
#                 'sentence': 'Video Analysis is subclass of Data Science Task',
#                 'source': '20241015_MISSION_KI_Glossar_v1.0 en.pdf',
#                 'page_number': 1,
#                 'start_index': 0
#             }

#         },
#     }

# relation = {
#         'source': {
#             'label': 'Image Analysis'
#         },
#         'target': {
#             'label': 'Data Science Task'
#         },
#         'edge': {
#             'label': 'is subclass of',
#             'properties': {
#                 'sentence': 'Image Analysis is subclass of Data Science Task',
#                 'source': '20241015_MISSION_KI_Glossar_v1.0 en.pdf',
#                 'page_number': 1,
#                 'start_index': 0
#             }

#         },
#     }


# res = add_to_graph(relation)
# print(res)


Cypher_query = """ 
            MATCH (n)-[r:is_subclass_of]->(req:Node{label:"data_science_task"}) 
            RETURN DISTINCT r.sentence  as sentence
        """
    
graph = get_graph(Cypher_query)
print(graph)