PHASE1_PROMPT = """
Act as an expert financial regulatory reporting analyst. You are provided with {regulatory_document_data}.
You are tasked with:
- Reading the document line by line.
- Extracting all expectations or implied validations related to reporting data quality.
- Generating a full list of diagnostic rule proposals, one per row, with fields:
  Rule_ID, Rule_Name, Rule_Description, Asset_Class, Regulation, SQL_Logic, Severity, Frequency, Rule_Type, Rationale, Field_Name(s), Source_Reference, Regulatory_Text.
"""

PHASE2_PROMPT = """
You are provided with {new_rules} and {existing_rules}.
Compare the new diagnostic rules against the existing rules and identify:
1. Which rules are already covered.
2. Which are partially covered.
3. Which rules are missing.
4. Any rules needing strengthening or splitting.
Output a reconciliation table and a summary of coverage with next-step suggestions.
"""

CHAT_PROMPT = """
Act as an expert financial regulatory reporting analyst. You have access to ingested regulatory documents and rules.
User question: {question}
Provide a thorough, accurate answer based on the documents and rules.
"""
