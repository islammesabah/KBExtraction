import os
import json
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

# Neo4j configuration
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "Tom27@jerry")

def fetch_all_data():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    query = """
    MATCH (n)-[r]->(m)
    RETURN n, r, m
    """
    
    print(f"Connecting to Neo4j at {NEO4J_URI}...")
    
    try:
        with driver.session() as session:
            result = session.run(query)
            nodes = []
            edges = []
            node_ids = set()
            
            print("Fetching data...")
            count = 0
            for record in result:
                n = record['n']
                m = record['m']
                r = record['r']
                
                if n.element_id not in node_ids:
                    nodes.append({
                        "id": n.element_id,
                        "labels": list(n.labels),
                        "properties": dict(n)
                    })
                    node_ids.add(n.element_id)
                
                if m.element_id not in node_ids:
                    nodes.append({
                        "id": m.element_id,
                        "labels": list(m.labels),
                        "properties": dict(m)
                    })
                    node_ids.add(m.element_id)

                edges.append({
                    "id": r.element_id,
                    "source": n.element_id,
                    "target": m.element_id,
                    "type": type(r).__name__,
                    "properties": dict(r)
                })
                count += 1
            
            print(f"Fetched {len(nodes)} nodes and {len(edges)} relationships.")
            
            output_data = {"nodes": nodes, "edges": edges}
            
            # Save to file
            output_file = "neo4j_dump.json"
            with open(output_file, 'w') as f:
                json.dump(output_data, f, indent=2)
            
            print(f"Data saved to {os.path.abspath(output_file)}")
            return output_data

    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.close()

if __name__ == "__main__":
    fetch_all_data()
