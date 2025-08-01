import pandas as pd
from neo4j import GraphDatabase
import openai
from config import KEY_COL, SUMMARY_COL, DESCRIPTION_COL

def ensure_constraints(driver):
    """
    Creates a uniqueness constraint on Issue.key.
    """
    with driver.session() as session:
        session.run(
            """
            CREATE CONSTRAINT IF NOT EXISTS
              FOR (i:Issue)
              REQUIRE i.key IS UNIQUE
            """
        )

def load_jira_csv(path: str) -> pd.DataFrame:
    """
    Reads the JIRA extract CSV into a pandas DataFrame and validates required columns.
    """
    df = pd.read_csv(path)
    for col in (KEY_COL, SUMMARY_COL, DESCRIPTION_COL):
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")
    return df

def ingest_and_embed(driver, df: pd.DataFrame):
    """
    For each row in df:
      1) Embed Summary+Description via OpenAI.
      2) MERGE Issue node with embedding.
      3) MERGE dynamic nodes for all other columns and relationships.
    """
    safe_names = {col: col.replace(" ", "_") for col in df.columns}
    with driver.session() as session:
        for _, row in df.iterrows():
            key = row[KEY_COL]
            summary = row.get(SUMMARY_COL, "") or ""
            desc = row.get(DESCRIPTION_COL, "") or ""

            # Build text and get embedding
            text = f"{summary}\n\n{desc}"
            emb_response = openai.Embedding.create(
                model="text-embedding-ada-002",
                input=text
            )
            embedding = emb_response["data"][0]["embedding"]

            # Merge Issue node with embedding
            session.run(
                """
                MERGE (i:Issue {key: $key})
                SET i.summary = $summary,
                    i.description = $description,
                    i.embedding = $embedding
                """,
                {"key": key, "summary": summary, "description": desc, "embedding": embedding}
            )

            # Merge dynamic property nodes
            for raw_col, safe_col in safe_names.items():
                if raw_col in (KEY_COL, SUMMARY_COL, DESCRIPTION_COL):
                    continue
                val = row[raw_col]
                if pd.isna(val) or str(val).strip() == "":
                    continue
                for part in str(val).split(";"):
                    v = part.strip()
                    session.run(
                        f"""
                        MERGE (n:`{safe_col}` {{value: $v}})
                        WITH n
                        MATCH (i:Issue {{key: $key}})
                        MERGE (i)-[:HAS_{safe_col.upper()}]->(n)
                        """,
                        {"v": v, "key": key}
                    )
