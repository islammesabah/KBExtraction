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
# This ensures that there are no duplicate Concept nodes with the same name (i.e., two nodes can't have the same name.)
# It makes merges idempotent (no duplicates if you re-import).
graph_instance.query("""
CREATE CONSTRAINT concept_name IF NOT EXISTS
FOR (c:Concept) REQUIRE c.name IS UNIQUE
""")
# "Concept" is just a label, a "kind" of node, representing concepts in the graph database.
# 💡 Why the label is Concept
# That’s just a name we chose to describe "things" or "entities" in our graph.
# In our case, each "thing" (like human_dignity, data_preprocessing, classification) is a concept, so it makes sense semantically.
# We could have called it :Entity, :Node, or even :Thing
# So, Concept is just a convenient, readable label.
# We used `Concept` because our CSVs contain concepts and relationships between them.
# i.e., conceptual relationships (like "classification is a subclass of supervised_learning")


# -------------------------------------------------------------------
# 4. Load CSV data
# -------------------------------------------------------------------
# import local CSV (semicolon separated)
path = "Data/seed/edges.csv"
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
query = """
UNWIND $rows AS row
MERGE (s:Concept {name: row.source})
MERGE (d:Concept {name: row.destination})
MERGE (s)-[r:REL {type: row.relationship}]->(d)
WITH collect(DISTINCT s) + collect(DISTINCT d) AS all_nodes, collect(r) AS rels
RETURN 
  size(apoc.coll.toSet(all_nodes)) AS total_nodes,
  size(rels) AS total_relationships
"""

res = graph_instance.query(query, params={"rows": rows})

print(f"[Import] ✅ Successfully imported edges: {res}")

# Note: MERGE is like "find or create". It ensures no duplicate nodes or relationships are created.
# UNWIND ==> loops over all rows from the Python list `$rows` and processes each row as `row`.
# MERGE (s:Concept {...}) ==> finds or creates a node labeled `Concept` with the given name (e.g., "human_dignity").
# MERGE (t:Concept {...}) ==> finds or creates a node labeled `Concept` with the given name (e.g., "intrinsic_worth").
# MERGE (s)-[]->(d) ==> finds or creates a relationship `:REL` from the source to the destination node.
# RETURN count(r) ==> returns the number of relationships created.
# 💡 Note: REL is a generic relationship type. We store the actual relationship type in a property called "type".
# 💡 This allows us to have multiple different relationships between the same nodes.