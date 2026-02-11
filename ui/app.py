import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
env_path = REPO_ROOT / ".env"
# SRC_DIR = REPO_ROOT / "src"
# if str(SRC_DIR) not in sys.path:
#     sys.path.insert(0, str(SRC_DIR))


import os
from flask import Flask, render_template, jsonify, request
from neo4j import GraphDatabase
from dotenv import load_dotenv
from kbdebugger.graph import get_graph

# Load .env from repo root (one level up)
# That explicitly tells Flask: Go one directory up and load the root .env
load_dotenv(dotenv_path=env_path)

app = Flask(__name__)

# Neo4j configuration
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "xx")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

def get_db():
    if not driver:
        return None
    return driver.session()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/graph')
def get_graph():
    query = """
    MATCH (n)-[r]->(m)
    RETURN n, r, m
    LIMIT 100
    """
    try:
        with driver.session() as session:
            result = session.run(query)
            nodes = []
            edges = []
            node_ids = set()

            for record in result:
                n = record['n']
                m = record['m']
                r = record['r']

                if n.element_id not in node_ids:
                    nodes.append({
                        "data": {
                            "id": n.element_id,
                            "label": n.get("name", "Unnamed"),
                            "properties": dict(n)
                        }
                    })
                    node_ids.add(n.element_id)
                
                if m.element_id not in node_ids:
                    nodes.append({
                        "data": {
                            "id": m.element_id,
                            "label": m.get("name", "Unnamed"),
                            "properties": dict(m)
                        }
                    })
                    node_ids.add(m.element_id)

                edges.append({
                    "data": {
                        "id": r.element_id,
                        "source": n.element_id,
                        "target": m.element_id,
                        "label": type(r).__name__,
                        "properties": dict(r)
                    }
                })

            return jsonify({"elements": {"nodes": nodes, "edges": edges}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/search_node', methods=['POST'])
def search_node():
    data = request.json
    node_name = data.get('name')
    if not node_name:
        return jsonify({"error": "No name provided"}), 400

    # Find the node, and all directly connected relationships and nodes
    query = """
    MATCH (n {name: $name})-[r]-(m)
    RETURN n, r, m
    """
    try:
        with driver.session() as session:
            result = session.run(query, name=node_name)
            
            # Format explicitly for the "textual details" requirement
            # "source(name) edge(name) destination(name)"
            # Note: The query matches (n)-[r]-(m), directionality needs care for "source" vs "dest" visualization
            # But the user asked for: source(name) edge(name) destination(name)
            # We will return list of strings.
            
            text_details = []
            graph_data = {"nodes": [], "edges": []}
            node_ids = set()
            
            for record in result:
                n = record['n'] # Our target node (usually, but Cypher might swap if not directed)
                r = record['r']
                m = record['m'] # The other node

                # Construct sentence
                # Determine actual source/target based on relationship start/end nodes
                start_node = n if r.start_node.element_id == n.element_id else m
                end_node = m if r.end_node.element_id == m.element_id else n
                
                sentence = f"{start_node.get('name', 'Unknown')} {r.type} {end_node.get('name', 'Unknown')}"
                text_details.append(sentence)

                # Collect graph data for highlighting if needed (or client does it)
                # Client side filtering is requested, but receiving structured text is also requested.
            
            return jsonify({"details": text_details})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def extract_knowledge(content):
    """
    Simulated knowledge extraction.
    Parses simple format: "Source, Relationship, Destination" per line.
    Or just returns mock data if parsing fails/is too simple.
    """
    triplets = []
    lines = content.split('\n')
    for line in lines:
        parts = [p.strip() for p in line.split(',')]
        if len(parts) >= 3:
            triplets.append({"source": parts[0], "relation": parts[1], "target": parts[2]})
    
    # Fallback/Mock data if empty (for demonstration)
    if not triplets:
        triplets = [
            {"source": "LogisticRegression", "relation": "HAS_HYPERPARAMETER", "target": "C"}, # Existing
            {"source": "LogisticRegression", "relation": "OPTIMIZES", "target": "LogLoss"}, # New relation, existing nodes?
            {"source": "NewAlgorithm", "relation": "IS_A", "target": "Algorithm"} # Completely new
        ]
    return triplets

import io
from flask import Flask, render_template, jsonify, request
from neo4j import GraphDatabase
from dotenv import load_dotenv
from pypdf import PdfReader

load_dotenv(dotenv_path=env_path)

# ... (rest of imports)

@app.route('/api/upload_verify', methods=['POST'])
def upload_verify():
    if 'document' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['document']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    try:
        if file.filename.lower().endswith('.pdf'):
            reader = PdfReader(file)
            content = ""
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    content += text + "\n"
        else:
            # Fallback for text files
            content = file.read().decode('utf-8', errors='replace')
        
        # Simplified: Return raw content for display in all tabs
        return jsonify({
            "existing": content,
            "partial": content,
            "new": content
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5002)
