# Regulatory Document RAG Application

## Overview
This Streamlit application allows you to:
1. Upload regulatory documents (PDF, Word, TXT) to extract diagnostic rules.
2. Upload an existing rules CSV to reconcile coverage.
3. Engage in a conversational Q&A about the ingested documents.

## Setup
1. Clone the repo.
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set your OpenAI API key:
   ```
   export OPENAI_API_KEY="YOUR_KEY"
   ```

## Running
```
streamlit run main.py
```

## File Structure
- `main.py`: Streamlit app entrypoint.
- `prompts.py`: Default prompt templates.
- `utils.py`: Helpers for ingestion, chunking, LLM calls.
- `requirements.txt`: Python dependencies.
- `README.md`: This file.
