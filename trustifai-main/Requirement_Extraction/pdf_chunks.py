import fitz  # PyMuPDF
import re
import spacy
# from langchain.schema import Document
from langchain_core.documents import Document
from langchain_community.document_loaders import UnstructuredPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import logging
import os


def extract_text_with_metadata(pdf_path):
    loader = UnstructuredPDFLoader(pdf_path)
    data = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=70, add_start_index=True)
    return text_splitter.split_documents(data)


def clean_extracted_text(chunks):
    cleaned_chunks = []

    for chunk in chunks:
        text = chunk.page_content
        start_index = chunk.metadata['start_index']
        source = chunk.metadata['source']
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            # Skip lines with DOIs
            if re.search(r'doi:\s*\d+\.\d+/\S+', line, re.IGNORECASE):
                continue
            # Skip lines starting with numbers followed by ':' or '.'
            if re.match(r'^\d+[:.]', line):
                continue
            # Skip lines containing email addresses
            if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', line):
                continue
            # Skip lines containing specific keywords
            if re.search(r'(Received|revised|accepted|Keywords|Abstract)', line, re.IGNORECASE):
                continue
            # Skip lines that are standalone numbers
            if re.match(r'^\d+$', line.strip()):
                continue
            # Optionally skip very short lines
            # if len(line.strip()) < 20:
                # continue
            # Fix hyphenated line breaks (e.g., "retrieval-\n augmented")
            line = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', line)
            # Replace multiple spaces with a single space
            line = re.sub(r'\s+', ' ', line)
            cleaned_lines.append(line.strip())

        # Preserve paragraph breaks by joining with double newline
        cleaned_text = '\n'.join(cleaned_lines) # can give \n\n
        cleaned_chunks.append({
            'source': source,
            'start_index': start_index,
            'cleaned_text': cleaned_text
        })

    return cleaned_chunks

def structure_sentences(chunks):
    documents = []
    for chunk in chunks:
        start_index = chunk['start_index']
        source = chunk['source']
        doc = Document(
                page_content=chunk['cleaned_text'],
                metadata={
                    'page_number': start_index,
                    'source': source
                }
            )
        documents.append(doc)
    return documents

def create_chunks(pdf_path):
    docs = extract_text_with_metadata(pdf_path) 
    if not docs:
        print("No text extracted from the PDF.")
        return

    cleaned_chunks = clean_extracted_text(docs)

    # Structure sentences using LangChain's Document with metadata
    return structure_sentences(cleaned_chunks)

