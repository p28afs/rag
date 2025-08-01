import os
import openai

# Neo4j connection settings
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# OpenAI API key for embeddings
openai.api_key = os.getenv("OPENAI_API_KEY")

# Core CSV column names
KEY_COL = "Issue key"
SUMMARY_COL = "Summary"
DESCRIPTION_COL = "Description"
