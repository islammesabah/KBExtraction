from kbdebugger.graph import get_graph

graph = get_graph()

cypher = """
MATCH (n:Node)-[r:REL]->(m:Node)
RETURN
  n.label AS source,
  m.label AS target,
  r.type AS predicate,
  properties(r) AS props
LIMIT $limit
"""

rels = graph.query_relations(cypher, params={"limit": 10})

# rows = graph.query(cypher)
# e.g., first row:
# {
#   'source': 'human_dignity', 
#   'target': 'intrinsic_worth', 
#   'predicate': 'means', 
#   'props': {
#       'sentence': 'human_dignity means intrinsic_worth', 
#       'type': 'means'
#   }
# }

for rel in rels:
    print(rel["source"]["label"], rel["edge"]["label"], rel["target"]["label"])
    print(rel["edge"]["properties"])

