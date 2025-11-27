import fitz  # PyMuPDF
import re
import spacy
from kbdebugger.compat.langchain import Document
import logging
import os

# Initialize SpaCy's English model
# need to download the model using the command: python -m spacy download en_core_web_sm
nlp = spacy.load('en_core_web_sm')

def extract_text_with_metadata(pdf_path, page_limit=None):
    try:
        with fitz.open(pdf_path) as file:
            logging.info("PDF opened successfully.")

            filename = os.path.basename(pdf_path) # e.g., 'data/SDS/20241015_MISSION_KI_Glossar_v1.0 en.pdf' -> '20241015_MISSION_KI_Glossar_v1.0 en.pdf'
            title, _ = os.path.splitext(filename) # splits at the last period

            #return "\n".join(page.get_text() for page in file)
            pages_text = []
            for page_num in range(len(file) if page_limit is None else min(len(file), page_limit)):
                page = file.load_page(page_num)
                text = page.get_text("text").strip()
                pages_text.append({
                    'page_number': page_num + 1,  # 1-indexed
                    'text': text
                })
            return title, pages_text

    except Exception as e:
        logging.error(f"Error extracting text from PDF: {e}")
        return "Untitled Document", []

def clean_extracted_text(raw_text):
    cleaned_pages = []

    for page in raw_text:
        text = page['text']
        page_number = page['page_number']
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
            # Thus, "retrieval-\n augmented" becomes "retrievalaugmented"
            line = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', line)
            # Replace multiple spaces with a single space
            line = re.sub(r'\s+', ' ', line)
            cleaned_lines.append(line.strip())

        # Preserve paragraph breaks by joining with double newline
        cleaned_text = '\n'.join(cleaned_lines) # can give \n\n
        cleaned_pages.append({
            'page_number': page_number,
            'cleaned_text': cleaned_text
        })

    return cleaned_pages

def tokenize_sentences(cleaned_pages):
    tokenized_pages = []

    for page in cleaned_pages:
        text = page['cleaned_text']
        page_number = page['page_number']
        doc = nlp(text) # This will segment the text into sentences using SpaCy
        sentences = [sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > 20]
        # .strip to remove leading/trailing spaces
        # We ignore very short sentences (<20 chars)
        tokenized_pages.append({
            'page_number': page_number,
            'sentences': sentences
        })
    return tokenized_pages

def structure_sentences(tokenized_pages, title):
    documents = []
    for page in tokenized_pages:
        page_number = page['page_number']
        for sentence in page['sentences']:
            doc = Document(
                page_content=sentence,
                metadata={
                    'page_number': page_number,
                    'source': title
                }
            )
            documents.append(doc)
    return documents

def create_sentences(pdf_path):
    title, pages_raw_text = extract_text_with_metadata(pdf_path)
    if not pages_raw_text:
        print("No text extracted from the PDF.")
        return

    cleaned_pages = clean_extracted_text(pages_raw_text)

    # Tokenize into sentences
    tokenized_pages = tokenize_sentences(cleaned_pages)

    # Structure sentences using LangChain's Document with metadata
    return structure_sentences(tokenized_pages, title)

