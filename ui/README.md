# Trustworthy AI Knowledge Discovery

This application visualizes and verifies knowledge from documents against a Neo4j knowledge graph.

## Prerequisites

- **Python 3.8+**
- **Neo4j Database** (Running locally or remotely)
- **Git**

## Setup

1.  **Clone the repository** (if applicable) or extract the project folder.

2.  **Configure Environment Variables**:
    Create a `.env` file in the root directory (if not already present) and add your Neo4j credentials:
    ```env
    NEO4J_URI=neo4j://localhost:7687
    NEO4J_USER=neo4j
    NEO4J_PASSWORD=your_password
    ```

3.  **Run the Setup Script**:
    We have provided a convenience script to set up the environment and install dependencies.
    ```bash
    ./setup.sh
    ```
    *This will create a virtual environment (`venv`) and install all required packages.*

## Running the Application

To start the server, you can use the run script:

```bash
./run.sh
```

Or manually:

1.  Activate the virtual environment:
    ```bash
    source venv/bin/activate
    ```
2.  Run the app:
    ```bash
    python app.py
    ```

The application will be available at [http://127.0.0.1:5001](http://127.0.0.1:5001).

## Features

- **Knowledge Graph Visualization**: Interactive graph view of AI trustworthiness concepts.
- **Document Upload & Verification**: Upload text or PDF files to verify their content against existing knowledge in the graph.
    - **Existing**: Facts already in the graph.
    - **Partial**: Facts where entities exist but the relationship is new.
    - **New**: Completely new facts.
- **Search**: Filter nodes by name.

## Troubleshooting

- **Port 5001 already in use**: If you see this error, another instance of the app is likely running. Stop it or kill the process using port 5001.
