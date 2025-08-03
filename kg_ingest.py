import streamlit as st
import pandas as pd
from neo4j import GraphDatabase
from langchain.embeddings import OpenAIEmbeddings
import os

# ------------------------------
# 1. Streamlit UI Components
# ------------------------------

def setup_ui():
    st.set_page_config(page_title="JIRA CSV → Knowledge Graph & Embeddings", layout="wide")
    st.title("JIRA CSV to Neo4j Knowledge Graph & Embedding Viewer")
    st.sidebar.header("Neo4j Connection Settings")
    uri = st.sidebar.text_input("Bolt URI", value=os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    user = st.sidebar.text_input("Username", value=os.getenv("NEO4J_USER", "neo4j"))
    pwd = st.sidebar.text_input("Password", type="password", value=os.getenv("NEO4J_PASSWORD", "password"))
    uploaded = st.file_uploader("Upload JIRA CSV", type=["csv"])
    return uri, user, pwd, uploaded

# ------------------------------
# 2. Data Preprocessing
# ------------------------------

def preprocess_data(uploaded_csv):
    # Load and fill nulls
    df = pd.read_csv(uploaded_csv)
    df = df.fillna('Unknown')

    # Combine summary + description for embedding
    df['combined'] = df['Summary'].str.strip() + ". " + df['Description'].str.strip()

    # Determine dynamic relationship columns
    static = {
        'Issue Key', 'Summary', 'Description', 'combined', 'embedding',
        'Issue Type', 'Status', 'Original Estimate', 'Story Points', 'Time Spent'
    }
    rel_cols = [col for col in df.columns if col not in static]

    return df, rel_cols

# ------------------------------
# 3. Embedding Generation
# ------------------------------

def compute_embeddings(df):
    embeddings = OpenAIEmbeddings()
    with st.spinner("Computing embeddings…"):
        vectors = embeddings.embed_documents(df['combined'].tolist())
    df['embedding'] = vectors
    return df

# ------------------------------
# 4. Neo4j Ingestion Logic
# ------------------------------

def ingest_to_neo4j(df, rel_cols, uri, user, pwd):
    driver = GraphDatabase.driver(uri, auth=(user, pwd))

    def ingest_row(tx, row):
        key = row['Issue Key']
        # Create or update Issue node with static and embedding properties
        props = {
            'key': key,
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
            SET i.summary=$summary, i.description=$description, i.embedding=$embedding,
                i.type=$type, i.status=$status,
                i.original_estimate=$original_estimate, i.story_points=$story_points,
                i.time_spent=$time_spent
            """, **props)

        # Create dynamic relationships
        for col in rel_cols:
            values = [v.strip() for v in str(row[col]).split(',') if v.strip()]
            if not values:
                continue
            node_label = ''.join([w.capitalize() for w in col.rstrip('s').replace(' ', '_').split('_')])
            rel_type = col.upper().replace(' ', '_').rstrip('S')
            for val in values:
                tx.run(
                    f"""
                    MERGE (n:`{node_label}` {{name:$val}})
                    WITH n
                    MATCH (i:Issue {{key:$key}})
                    MERGE (i)-[:`{rel_type}`]->(n)
                    """, val=val, key=key)

    with driver.session() as session:
        with st.spinner("Ingesting data into Neo4j…"):
            for _, row in df.iterrows():
                session.write_transaction(ingest_row, row)
    driver.close()

# ------------------------------
# Main App Flow
# ------------------------------

def main():
    uri, user, pwd, uploaded = setup_ui()
    if not uploaded:
        st.info("Please upload a JIRA CSV extract to begin.")
        return

    df, rel_cols = preprocess_data(uploaded)
    st.success(f"Loaded {len(df)} records from CSV.")

    df = compute_embeddings(df)

    # Preview vectorized issues
    st.subheader("Vectorized Issue Data Preview")
    for _, row in df.iterrows():
        with st.expander(f"{row['Issue Key']} - Embedding"):
            st.markdown(
                f"**JIRA ID:** {row['Issue Key']}  \n"
                f"**SUMMARY:** {row['Summary']}  \n"
                f"**DESCRIPTION:** {row['Description']}  \n"
                f"**EMBEDDING VECTOR:** {row['embedding']}")

    if st.button("Ingest to Neo4j"):
        ingest_to_neo4j(df, rel_cols, uri, user, pwd)
        st.success("Data ingestion complete with dynamic relationships!")

if __name__ == '__main__':
    main()
