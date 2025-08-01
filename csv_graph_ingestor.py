import pandas as pd
from langchain.schema import Document  # or whichever type you wrap chunks in

class KnowledgeGraphIngestor:
    # … your existing PDF methods …

    async def extract_csv_rows(
        self,
        namespace: str,
        document_name: str,
        uploaded_csv_file,
        update_callback=None,
    ) -> list[pd.Series]:
        """
        Read the uploaded CSV into a pandas DataFrame,
        return raw Series rows for further processing.
        """
        self.logger.info(f"[{namespace}] {document_name}: reading CSV {uploaded_csv_file.name}…")
        try:
            df = pd.read_csv(uploaded_csv_file)
            self.logger.info(f"[{namespace}] {document_name}: loaded {len(df)} rows.")
            # Optionally call update_callback with progress here
            return list(df.itertuples(index=False, name=None))
        except Exception as e:
            self.logger.error(f"[{namespace}] {document_name} ✖ CSV read error: {e}")
            return []

    async def extract_csv_and_split_into_chunks(
        self,
        namespace: str,
        document_name: str,
        uploaded_csv_file,
        metadata_template: dict,
        update_callback=None,
    ) -> list[Document]:
        """
        Full CSV → chunk pipeline.  
        1) extract_csv_rows → list of tuples  
        2) for each row, build a text blob (Summary + Description)  
        3) build metadata dict from all other columns  
        4) call your existing text‐splitter to chunk it  
        """
        rows = await self.extract_csv_rows(namespace, document_name, uploaded_csv_file, update_callback)
        chunks: list[Document] = []

        # read headers once
        df_head = pd.read_csv(uploaded_csv_file, nrows=0)
        cols = list(df_head.columns)
        KEY_COL = "Issue key"
        SUMMARY_COL = "Summary"
        DESC_COL = "Description"

        for row in rows:
            # pandas.itertuples with name=None gives plain tuple in column order
            vals = dict(zip(cols, row))

            # build the text payload
            text = f"{vals.get(SUMMARY_COL,'')}\n\n{vals.get(DESC_COL,'')}"

            # metadata: start with whatever template you have,
            # then merge _all_ other fields except summary/desc/text
            meta = metadata_template.copy()
            meta["key"] = vals.get(KEY_COL)
            for c in cols:
                if c in (KEY_COL, SUMMARY_COL, DESC_COL):
                    continue
                v = vals.get(c)
                if pd.isna(v) or v == "":
                    continue
                meta[c] = v

            # now split into chunks via your existing splitter
            # assume you have an async method: self.split_text_into_chunks(text, meta, ...)
            new_chunks = await self.split_text_into_chunks(
                namespace=namespace,
                document_name=document_name,
                text=text,
                metadata=meta,
                update_callback=update_callback,
            )

            self.logger.info(
                f"[{namespace}] {document_name}: row {meta['key']} → {len(new_chunks)} chunks."
            )
            chunks.extend(new_chunks)

        return chunks
