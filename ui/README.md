# Knowledge-based Debugger for Trustworthy AI

This application visualizes and verifies knowledge extracted from documents against a Neo4j knowledge graph.

---

## Prerequisites

- **Python 3.9+** (recommended)
- **Neo4j Database** (running locally or remotely)
- **Git**

---

## 🚀 Quick Start (2 Commands)

After cloning the repository and configuring `.env`:

```bash
./setup.sh
./ui/run.sh
````

The application will then be available at:

```
http://127.0.0.1:5002
```

---

## Setup (Run Once)

### 1. Clone the Repository

```bash
git clone https://github.com/islammesabah/KBExtraction.git
cd `KBExtraction`
```

### 2. Configure Environment Variables

Create a `.env` file in the project root and add your credentials:

```env
NEO4J_URI=neo4j://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
GROQ_API_KEY=your_api_key
```

### 3. Run the Setup Script

```bash
./setup.sh
```

This script will:

* Create a virtual environment (`.venv/`)
* Install all dependencies from the locked requirements file
* Ensure CPU-only PyTorch is installed for compatibility and efficiency

You only need to run this again if dependencies change.

---

## Running the Application

To start the application locally:

```bash
./ui/run.sh
```

The script will:

* Activate the virtual environment
* Set the correct `PYTHONPATH`
* Start the Flask server

The application will be available at:

```
http://127.0.0.1:5002
```

---

## Project Structure (Relevant Files)

```
ui/setup.sh                 # One-time environment setup
ui/run.sh                   # Local development entry point
src/kbdebugger              # Core backend
.venv/                      # Virtual environment (auto-created)
```

---

## Features

### 🔎 Knowledge Graph Visualization

Interactive graph exploration of AI trustworthiness concepts.

### 📄 Document Upload & Verification

Upload text or PDF documents and compare extracted facts against the Neo4j knowledge graph:

* **Existing** – Fact already exists in the graph
* **Partial** – Entities exist but the relationship is new
* **New** – Completely new knowledge

### 🧠 Keyword Filtering

Filter extracted content by search keyword.

### 🛠 Triplet Oversight & Validation

Manual validation and refinement of extracted knowledge triplets before graph insertion.

---

## Troubleshooting

### Port 5002 Already in Use

If you see an error that port `5002` is already in use:

```bash
lsof -i :5002
```

Then terminate the process:

```bash
kill -9 <PID>
```

---

## Notes

* The project uses a reproducible dependency setup (`requirements.lock.txt`).
* The virtual environment is created automatically inside the project directory.