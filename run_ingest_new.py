import streamlit as st
import pandas as pd
from neo4j import GraphDatabase
from langchain.embeddings import OpenAIEmbeddings
import os

# ------------------------------
# Helper Functions
# ------------------------------

def parse_multi_values(cell_value):
    """
    Splits a comma-separated field into individual values,
    trimming whitespace and ignoring empty entries.
    """
    return [v.strip() for v in str(cell_value).split(',') if v.strip()]

# ------------------------------
# Ensure Uniqueness Constraints
# ------------------------------

def ensure_constraints(driver):
    """
    Creates uniqueness constraints if they do not already exist.
    """
    queries = [
        "CREATE CONSTRAINT IF NOT EXISTS ON (i:Issue) ASSERT i.key IS UNIQUE;",
        "CREATE CONSTRAINT IF NOT EXISTS ON (r:Regulator) ASSERT r.name IS UNIQUE;",
        "CREATE CONSTRAINT IF NOT EXISTS ON (m:Mandate) ASSERT m.code IS UNIQUE;",
        "CREATE CONSTRAINT IF NOT EXISTS ON (a:Assignee) ASSERT a.name IS UNIQUE;",
        "CREATE CONSTRAINT IF NOT EXISTS ON (l:Label) ASSERT l.name IS UNIQUE;",
        "CREATE CONSTRAINT IF NOT EXISTS ON (v:Version) ASSERT v.name IS UNIQUE;"
    ]
    with driver.session() as session:
        for q in queries:
            session.run(q)

# ------------------------------
# Streamlit UI Setup
# ------------------------------

def setup_ui():
    """
    Configures Streamlit sidebar for Neo4j credentials and CSV upload.
    """
    st.set_page_config(page_title="JIRA CSV → Knowledge Graph & Embedding Viewer", layout="wide")
    st.title("JIRA CSV to Neo4j Knowledge Graph & Embedding Viewer")

    st.sidebar.header("Neo4j Connection Settings")
    uri = st.sidebar.text_input("Bolt URI", value=os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    user = st.sidebar.text_input("Username", value=os.getenv("NEO4J_USER", "neo4j"))
    pwd = st.sidebar.text_input("Password", type="password", value=os.getenv("NEO4J_PASSWORD", "password"))

    uploaded = st.file_uploader("Upload JIRA CSV", type=["csv"])
    return uri, user, pwd, uploaded

# ------------------------------
# Data Preprocessing
# ------------------------------

def preprocess_data(uploaded_csv):
    """
    Loads the CSV, fills nulls, combines text fields, and identifies relationship columns.
    """
    df = pd.read_csv(uploaded_csv)
    df = df.fillna('Unknown')

    # Combine summary + description for embeddings
    df['combined'] = df['Summary'].str.strip() + ". " + df['Description'].str.strip()

    # Static columns to exclude from relationships
    static_cols = {
        'Issue Key', 'Summary', 'Description', 'combined', 'embedding',
        'Issue Type', 'Status', 'Original Estimate', 'Story Points', 'Time Spent'
    }
    rel_cols = [col for col in df.columns if col not in static_cols]
    return df, rel_cols

# ------------------------------
# Embedding Generation
# ------------------------------

def compute_embeddings(df):
    """
    Uses LangChain OpenAIEmbeddings to vectorize combined text.
    """
    embedder = OpenAIEmbeddings()
    with st.spinner("Computing embeddings…"):
        vectors = embedder.embed_documents(df['combined'].tolist())
    df['embedding'] = vectors
    return df

# ------------------------------
# Neo4j Ingestion Logic
# ------------------------------

def ingest_to_neo4j(df, rel_cols, uri, user, pwd):
    """
    Establishes Neo4j connection, ensures constraints, and ingests nodes/relationships.
    """
    driver = GraphDatabase.driver(uri, auth=(user, pwd))
    ensure_constraints(driver)

    def ingest_row(tx, row):
        # Merge Issue node with properties
        props = {
            'key': row['Issue Key'],
            'summary': row['Summary'],
            'description': row['Description'],
            'embedding': row['embedding'],
            'type': row['Issue Type'],
            'status': row['Status'],
            'original_estimate': row['Original Estimate'],
            'story_points': row['Story Points'],
            'time_spent': row['Time Spent']
        }
        tx.run(
            """
            MERGE (i:Issue {key:$key})
            SET i.summary=$summary,
                i.description=$description,
                i.embedding=$embedding,
                i.type=$type,
                i.status=$status,
                i.original_estimate=$original_estimate,
                i.story_points=$story_points,
                i.time_spent=$time_spent
            """, **props)

        # Dynamic relationships from multi-valued columns
        for col in rel_cols:
            values = parse_multi_values(row[col])
            if not values:
                continue
            # Derive node label and relationship type
            singular = col.rstrip('s')
            node_label = ''.join(w.capitalize() for w in singular.replace(' ', '_').split('_'))
            rel_type = col.upper().replace(' ', '_').rstrip('S')
            for val in values:
                tx.run(
                    f"""
                    MERGE (n:`{node_label}` {{name:$val}})
                    WITH n
                    MATCH (i:Issue {{key:$key}})
                    MERGE (i)-[:`{rel_type}`]->(n)
                    """, val=val, key=row['Issue Key'])

    with driver.session() as session:
        with st.spinner("Ingesting data into Neo4j…"):
            for _, row in df.iterrows():
                session.write_transaction(ingest_row, row)
    driver.close()

# ------------------------------
# Main Application Flow
# ------------------------------

def main():
    uri, user, pwd, uploaded = setup_ui()
    if not uploaded:
        st.info("Please upload a JIRA CSV extract to begin.")
        return

    df, rel_cols = preprocess_data(uploaded)
    st.success(f"Loaded {len(df)} records from CSV.")

    df = compute_embeddings(df)

    # Preview embedded data
    st.subheader("Preview Vectorized Issues")
    for _, row in df.iterrows():
        with st.expander(f"{row['Issue Key']} - Embedding"):
            st.markdown(
                f"**JIRA ID:** {row['Issue Key']}  \n"
                f"**SUMMARY:** {row['Summary']}  \n"
                f"**DESCRIPTION:** {row['Description']}  \n"
                f"**EMBEDDING VECTOR:** {row['embedding']}" )

    if st.button("Ingest to Neo4j"):
        ingest_to_neo4j(df, rel_cols, uri, user, pwd)
        st.success("Data ingestion complete with dynamic relationships and constraints!")

if __name__ == '__main__':
    main()
