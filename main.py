import streamlit as st
from utils import load_documents, chunk_documents, generate_new_rules, load_existing_rules, reconcile_rules, conversational_qa
from prompts import PHASE1_PROMPT, PHASE2_PROMPT, CHAT_PROMPT

def main():
    st.set_page_config(page_title="Regulatory RAG App", layout="wide")
    st.title("Regulatory Document RAG Application")

    # Sidebar for prompt templates
    st.sidebar.header("Prompt Templates")
    phase1_prompt = st.sidebar.text_area("Phase 1 Prompt", value=PHASE1_PROMPT, height=200)
    phase2_prompt = st.sidebar.text_area("Phase 2 Prompt", value=PHASE2_PROMPT, height=200)
    chat_prompt = st.sidebar.text_area("Chat Prompt", value=CHAT_PROMPT, height=200)

    st.header("1. Upload Documents")
    regulatory_files = st.file_uploader("Upload Regulatory Documents (PDF/Word/Txt)", type=["pdf", "docx", "txt"], accept_multiple_files=True)
    existing_rules_file = st.file_uploader("Upload Existing Rules (CSV)", type=["csv"])

    new_rules_df = None
    if regulatory_files:
        st.info("Processing regulatory documents...")
        docs = load_documents(regulatory_files)
        chunks = chunk_documents(docs)
        new_rules_df = generate_new_rules(chunks, phase1_prompt)
        st.success("Extracted new diagnostic rules.")
        st.download_button("Download New Rules CSV", new_rules_df.to_csv(index=False), "new_rules.csv", "text/csv")

    if existing_rules_file and new_rules_df is not None:
        st.info("Reconciling with existing rules...")
        existing_df = load_existing_rules(existing_rules_file)
        recon_df, summary = reconcile_rules(new_rules_df, existing_df, phase2_prompt)
        st.success("Reconciliation complete.")
        st.download_button("Download Reconciliation CSV", recon_df.to_csv(index=False), "reconciliation.csv", "text/csv")
        st.markdown("### Coverage Summary")
        st.write(summary)

    st.header("2. Conversational Q&A")
    question = st.text_input("Ask a question about the regulatory documents:")
    if question:
        answer = conversational_qa(question, chat_prompt)
        st.write(answer)

if __name__ == "__main__":
    main()
