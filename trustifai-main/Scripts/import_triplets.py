import os, csv
from langchain_community.graphs import Neo4jGraph
from dotenv import load_dotenv

# -------------------------------------------------------------------
# 1. Load environment variables from .env in the project root
# -------------------------------------------------------------------
load_dotenv(override=True)

# -------------------------------------------------------------------
# 2. Connect to Neo4j
# -------------------------------------------------------------------
graph_instance = Neo4jGraph(
    url=os.getenv("NEO4J_URI"),
    username=os.getenv("NEO4J_USERNAME", "neo4j"),
    password=os.getenv("NEO4J_PASSWORD", "")
)

# -------------------------------------------------------------------
# 3. Create uniqueness constraint (safe to rerun)
# -------------------------------------------------------------------
# This ensures that there are no duplicate Node nodes with the same name (i.e., two nodes can't have the same name.)
# It makes merges idempotent (no duplicates if you re-import).
graph_instance.query("""
CREATE CONSTRAINT node_label IF NOT EXISTS
FOR (n:Node) REQUIRE n.label IS UNIQUE
""")
# "Node" is just a name, a "kind" of node, representing nodes or concepts in the graph database.
# 💡 Why the name Node
# That's just a name we chose to describe "things" or "entities" in our graph.
# In our case, each "thing" (like human_dignity, data_preprocessing, classification) is a node, so it makes sense semantically.
# We could have called it :Entity, :Concept, or even :Thing
# So, Node is just a convenient, readable name.

# Add indexes
graph_instance.query("""
CREATE INDEX node_label IF NOT EXISTS FOR (n:Node) ON (n.label);
CREATE INDEX rel_label  IF NOT EXISTS FOR ()-[r:REL]-() ON (r.label);
CREATE INDEX rel_created IF NOT EXISTS FOR ()-[r:REL]-() ON (r.created_at);
""")

# -------------------------------------------------------------------
# 4. Load CSV data
# -------------------------------------------------------------------
# import local CSV (semicolon separated)
path = "Data/seed/triplets.csv"
with open(path, newline='', encoding="utf-8") as f:
    reader = csv.DictReader(f, delimiter=';')  # source;relationship;destination
    # DictReader reads each row into a dictionary where keys are the column headers
    rows = [r for r in reader] # rows now is a list of dictionaries list[dict[str,str]]
    """ Example row:
    {
      "source": "human_dignity",
      "relationship": "means",
      "destination": "intrinsic_worth"
    }
    """

# -------------------------------------------------------------------
# 5. Batch insert (to Neo4j) using UNWIND for efficiency
# -------------------------------------------------------------------
# query = """
# UNWIND $rows AS row
# MERGE (s:Node {label: row.source})
# MERGE (d:Node {label: row.destination})
# MERGE (s)-[r:REL {type: row.relationship}]->(d)
# WITH collect(DISTINCT s) + collect(DISTINCT d) AS all_nodes, collect(r) AS rels
# RETURN 
#   size(apoc.coll.toSet(all_nodes)) AS total_nodes,
#   size(rels) AS total_relationships
# """

query = """
UNWIND $rows AS row
MERGE (s:Node    {label: row.source})
MERGE (d:Node    {label: row.destination})
MERGE (s)-[r:REL {type: row.relationship}]->(d)
ON CREATE SET r.sentence = row.source + ' ' + row.relationship + ' ' + row.destination
WITH collect(DISTINCT s) + collect(DISTINCT d) AS all_nodes, collect(r) AS rels
RETURN 
  size(apoc.coll.toSet(all_nodes)) AS total_nodes,
  size(rels) AS total_relationships
"""

res = graph_instance.query(query, params={"rows": rows})

print(f"[Import] ✅ Successfully imported edges: {res}")

# Note: MERGE is like "find or create". It ensures no duplicate nodes or relationships are created.
# UNWIND ==> loops over all rows from the Python list `$rows` and processes each row as `row`.
# MERGE (s:Node {...}) ==> finds or creates a node labeled `Node` with the given label (e.g., "human_dignity").
# MERGE (t:Node {...}) ==> finds or creates a node labeled `Node` with the given label (e.g., "intrinsic_worth").
# MERGE (s)-[]->(d) ==> finds or creates a relationship `:REL` from the source to the destination node.
# RETURN count(r) ==> returns the number of relationships created.
# 💡 Note: REL is a generic relationship type. We store the actual relationship type in a property called "type".
# 💡 This allows us to have multiple different relationships between the same nodes.