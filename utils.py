import hashlib
import os
import re
import pandas as pd
from datetime import datetime
from vertexai import init
from vertexai.generative_models import GenerativeModel
from google.oauth2 import service_account
from tika import parser
from dotenv import load_dotenv
from tqdm import tqdm
from mimetypes import guess_type
from PyPDF2 import PdfReader, PdfWriter
from ocr_processor import OCRProcessor

load_dotenv()

credentials_file_path = os.getenv('CREDENTIALS_FILE_PATH')
project_id = os.getenv('PROJECT_ID')
model = os.getenv('MODEL')

# Inisialisasi kredensial dari file service account
credentials = service_account.Credentials.from_service_account_file(credentials_file_path)
init(project=project_id, credentials=credentials)
multimodal_model = GenerativeModel(model)

def hash_file(filename):
    hasher = hashlib.sha256()
    with open(filename, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def call_gemini(prompt):
    responses = multimodal_model.generate_content([prompt], stream=True)
    full_result = ''
    for response in responses:
        full_result += response.text
    return full_result

def style_df(df):
    return df.style.apply(
        lambda x: ["background: #5fbe43" if v == 'found' else "background: #ffa7a7" for v in x], subset=['status'],
        axis=1
    ).set_table_attributes('border="1" class="dataframe table table-hover table-bordered"')

def status_check(status, detail):
    if not detail:
        return 'not found'
    detail = str(detail)
    if status.lower() == 'found':
        if len(detail) < 10:
            return 'not found'
        for i in ['not found', 'no match', 'not match', 'no details found']:
            if i in detail:
                return 'not found'
    if status.lower() == 'not found':
        if len(detail) > 10:
            ada = False
            for i in ['not found', 'no match', 'not match', 'no details found']:
                if i in detail:
                    ada = True
            if not ada:
                return 'found'
    return status

def split_pdf_per_15_pages(source_pdf_path, output_directory):
    basename = os.path.basename(source_pdf_path)
    reader = PdfReader(source_pdf_path)
    total_pages = len(reader.pages)
    num_files = (total_pages + 14) // 15
    for i in range(num_files):
        writer = PdfWriter()
        start_page = i * 15
        end_page = min(start_page + 15, total_pages)
        for page in range(start_page, end_page):
            writer.add_page(reader.pages[page])
        output_path = f"{output_directory}/{basename}_{i + 1}.pdf"
        with open(output_path, "wb") as output_pdf:
            writer.write(output_pdf)
        print(f"Part {i + 1} written with pages from {start_page + 1} to {end_page}.")
        yield output_path

def call_ocr(filename):
    ocr_processor = OCRProcessor(credentials_file_path)
    mime_type, _ = guess_type(filename)
    if mime_type == 'application/pdf':
        list_file = split_pdf_per_15_pages(filename, "./")
    else:
        list_file = [filename]
    all_text = []
    for file in list_file:
        with open(file, 'rb') as f:
            file_content = f.read()
        all_text.append(ocr_processor.process_ocr(
            project_id,
            os.getenv('LOCATION'),
            os.getenv('PROCESSOR_ID'),
            file_content,
            mime_type))
    return '\n'.join(all_text)

def main(list_bank_statement, list_file_invoice, merge_bill, version='premium', service='all'):
    bank_statement_text_list = []
    for filename_bank_statement in list_bank_statement:
        filesave = os.path.join('contents', f"{hash_file(filename_bank_statement)}_{version}.txt")
        if os.path.isfile(filesave):
            print('using last ocr', filename_bank_statement)
            with open(filesave, 'r') as f:
                content = f.read()
        else:
            if version == 'premium':
                content = call_ocr(filename_bank_statement)
            else:
                content = parser.from_file(filename_bank_statement)['content']
            with open(filesave, 'w') as f:
                f.write(content)
        bank_statement_text_list.append({"bank_statement_filename": filename_bank_statement, "text": content})

    invoice_text_list = []
    for file_invoice in tqdm(list_file_invoice):
        filesave = os.path.join('contents', f"{hash_file(file_invoice)}.txt")
        if os.path.isfile(filesave):
            print('using last ocr', file_invoice)
            with open(filesave, 'r') as f:
                content = f.read()
        else:
            content = call_ocr(file_invoice)
            with open(filesave, 'w') as f:
                f.write(content)
        invoice_text_list.append({"invoice_file": file_invoice, "text": content})

    analysis = ''
    matching = []

    if service in ['all', 'analysis']:
        print('analysis...')
        analysis = call_gemini(f"""Summarize all analyses and provide suggestions regarding whether the user should consider taking out loans and using HTML format.
        bank statement: {bank_statement_text_list}        
        """)

    if service in ['all', 'matching']:
        print('matching...')
        invoice_text_list.extend(merge_bill)
        matching_list = []
        for bank_statement_text in bank_statement_text_list:
            print('matching bank statement:', bank_statement_text['bank_statement_filename'])
            matching = call_gemini(
                f"""
                Please analyze the provided bank statement text to identify the specified invoice. 
                The matching rules should include the invoice date, total transaction amount, product name, or supplier name. 
                The invoice date should match the bank statement period with a maximum difference of 30 days (grace period). 
                Additionally, one invoice can have more than one match in the bank statement.
                Refer to the following details:

                Invoice Text: {invoice_text_list}
                
                Bank Statement Text: {bank_statement_text}

                The response should be formatted in JSON as follows:
                [{{
                  "invoice_file": filename_invoice,
                  "bank_statement_file": filename_bank_statement,
                  "status": "found" if invoice exist in bank statement or "not found" if not,
                  "supplier_name":"supplier from invoice",
                  "total_transaction":"total transaction on invoice",
                  "invoice_date":'<datetime>'
                  "transaction_match_detail": "Details of the transaction in the bank statement that matches the invoice text",
                  "reason": "Explanation the finding"
                }}]"""
            )
            null = None
            false = False
            true = True
            matching_list.extend(eval(re.findall(r'\[.*\]', matching, flags=re.I | re.S)[0]))

    return analysis, matching_list
