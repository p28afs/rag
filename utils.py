import pandas as pd
import tempfile
from PyPDF2 import PdfReader
import docx
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.llms import OpenAI
from langchain.chains import ConversationalRetrievalChain

def load_documents(files):
    texts = []
    for f in files:
        if f.type == "application/pdf":
            reader = PdfReader(f)
            texts.extend(page.extract_text() for page in reader.pages)
        elif f.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = docx.Document(f)
            texts.append("\n".join(p.text for p in doc.paragraphs))
        else:  # txt
            texts.append(f.read().decode("utf-8"))
    return texts

def chunk_documents(texts, chunk_size=1000, overlap=100):
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=overlap)
    return splitter.split_texts(texts)

def generate_new_rules(chunks, prompt_template):
    llm = OpenAI(temperature=0)
    rules = []
    for chunk in chunks:
        prompt = prompt_template.replace("{regulatory_document_data}", chunk)
        response = llm(prompt)
        # Assume CSV output
        df = pd.read_csv(io.StringIO(response))
        rules.append(df)
    return pd.concat(rules, ignore_index=True)

def load_existing_rules(file):
    return pd.read_csv(file)

def reconcile_rules(new_df, existing_df, prompt_template, batch_size=500):
    import io
    llm = OpenAI(temperature=0)
    results = []
    for start in range(0, len(new_df), batch_size):
        batch = new_df.iloc[start:start+batch_size]
        prompt = prompt_template.replace("{new_rules}", batch.to_csv(index=False)).replace("{existing_rules}", existing_df.to_csv(index=False))
        resp = llm(prompt)
        # Assume CSV table plus summary separated by delimiter
        table_csv, summary = resp.split("---SUMMARY---")
        results.append(pd.read_csv(io.StringIO(table_csv)))
        overall_summary = summary
    return pd.concat(results, ignore_index=True), overall_summary

def conversational_qa(question, prompt_template):
    embeddings = OpenAIEmbeddings()
    # Assumes FAISS index built elsewhere and saved
    db = FAISS.load_local("vectorstore", embeddings)
    qa = ConversationalRetrievalChain.from_llm(OpenAI(temperature=0), db.as_retriever())
    return qa({"question": question})["answer"]
