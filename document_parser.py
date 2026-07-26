import os
import pandas as pd
from typing import List
from llama_index.core import Document
from llama_index.readers.llama_parse import LlamaParse

async def advanced_parser_async(file_name: str, file_bytes: bytes, temp_path: str) -> List[Document]:
    """Asynchronously parses unstructured data via LlamaParse, handling tabular files locally."""
    documents = []
    
    if file_name.endswith('.txt'):
        text = file_bytes.decode("utf-8")
        documents.append(Document(
            text=text,
            metadata={"file_name": file_name, "file_type": "txt", "page_number": 1}
        ))
        
    elif file_name.endswith(('.csv', '.xlsx')):
        df = pd.read_csv(temp_path) if file_name.endswith('.csv') else pd.read_excel(temp_path)
        for idx, row in df.iterrows():
            serialized_row = ". ".join([f"{col}: {val}" for col, val in row.items() if pd.notna(val)])
            documents.append(Document(
                text=serialized_row,
                metadata={
                    "file_name": file_name, 
                    "file_type": "structured", 
                    "row_index": idx, 
                    "page_number": (idx // 50) + 1
                }
            ))
            
    else:
        parser = LlamaParse(
            result_type="markdown", 
            num_workers=8,           
            verbose=True
        )
        
        extracted_docs = await parser.aload_data(temp_path)
        
        for idx, doc in enumerate(extracted_docs):
            page_num = doc.metadata.get("page_label", str(idx + 1))
            documents.append(Document(
                text=doc.text,
                metadata={
                    "file_name": file_name, 
                    "file_type": os.path.splitext(file_name)[1][1:], 
                    "page_number": int(page_num) if page_num.isdigit() else idx + 1
                }
            ))
            
    return documents