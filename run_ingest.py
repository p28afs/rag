import sys
from neo4j import GraphDatabase
import config
import jira_ingestor

def main():
    # Connect to Neo4j
    driver = GraphDatabase.driver(
        config.NEO4J_URI,
        auth=(config.NEO4J_USER, config.NEO4J_PASSWORD)
    )

    # Ensure uniqueness constraint
    jira_ingestor.ensure_constraints(driver)

    # Determine CSV path
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = input("Enter path to JIRA CSV: ")

    # Load and ingest
    df = jira_ingestor.load_jira_csv(path)
    jira_ingestor.ingest_and_embed(driver, df)

    print(f"Ingested {len(df)} issues into Neo4j.")

if __name__ == "__main__":
    main()
