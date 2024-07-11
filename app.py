from flask import Flask, request, render_template, session, send_file
from werkzeug.utils import secure_filename
from tqdm import tqdm
import os, io,re, pandas as pd
from ocr_processor import OCRProcessor
from utils import hash_file, call_gemini, style_df, status_check, main
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

# Ensure that the 'uploads' directory exists
os.makedirs('uploads', exist_ok=True)
os.makedirs('contents', exist_ok=True)

@app.route('/')
def index():
    return render_template('index2.html')

@app.route('/v2')
def index2():
    return render_template('index2.html')

@app.route('/download')
def download_excel():
    output = io.BytesIO()
    df = pd.DataFrame(session.get('df'))
    filename = 'data_{}.xlsx'.format(datetime.now())
    with pd.ExcelWriter(filename) as writer:
        df.to_excel(writer, index=False)
    return send_file(filename, as_attachment=True)

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'bankStatement' not in request.files or 'invoices' not in request.files:
        return 'No file part'

    bank_statement = request.files.getlist('bankStatement')
    invoices = request.files.getlist('invoices')
    split_invoice = request.files.getlist('split_invoice')

    ocr_version = 'premium' if request.form.get('ocrVersion') == 'on' else 'free'
    processing_options = request.form.get('processingOptions')

    if not all(bs.filename for bs in bank_statement):
        return 'No selected file for one or more bank statement'
    if not all(invoice.filename for invoice in invoices):
        return 'No selected file for one or more invoices'

    merge_bill = []
    if any(bs.filename for bs in split_invoice):
        all_split_invoice = []
        for si in split_invoice:
            bill_filename = secure_filename(si.filename)
            si.save(os.path.join('uploads', bill_filename))
            bill_filename = os.path.join('uploads', bill_filename)

            filesave = os.path.join('contents', f"{hash_file(bill_filename)}.txt")
            if os.path.isfile(filesave):
                with open(filesave, 'r') as f:
                    content = f.read()
            else:
                content = call_ocr(bill_filename)
                with open(filesave, 'w') as f:
                    f.write(content)

            all_split_invoice.append({"invoice_file": bill_filename, "text": content})

        prompt = f"""berikut adalah list data invoice, gabungkan seluruh invoice pembayaran ini menjadi 1 dengan return JSON seperti berikut :
{{
"invoice_file":"Split Bill",
"text":{{
"invoice_date":"<date dari setiap invoice>",
"total amount transaction": "<sum dari seluruh invoice>"
"supplier_name":"supplier_name",
"product_name":"product name"}}
}}                    
                    List Invoice : {all_split_invoice}
                    """
        merge_bill = call_gemini(prompt)
        null = None
        false = False
        true = True

        merge_bill = [eval(re.findall(r'\{.*\}', merge_bill, flags=re.I | re.S)[0])]

    if bank_statement and invoices:
        list_bank_statement = []
        for bs in bank_statement:
            bank_statement_filename = secure_filename(bs.filename)
            bs.save(os.path.join('uploads', bank_statement_filename))
            list_bank_statement.append(os.path.join('uploads', bank_statement_filename))

        list_invoices = []
        for invoice in invoices:
            invoice_filename = secure_filename(invoice.filename)
            invoice.save(os.path.join('uploads', invoice_filename))
            list_invoices.append(os.path.join('uploads', invoice_filename))

        analysis, matching = main(list_bank_statement, list_invoices, merge_bill, ocr_version, processing_options)

        matching = pd.DataFrame(matching)
        for c in ['invoice_file', 'bank_statement_file']:
            matching[c] = matching[c].transform(lambda s: os.path.basename(s))

        matching['status'] = matching.apply(lambda s: status_check(s['status'], s['transaction_match_detail']), axis=1)

        session['df'] = matching.to_dict()

        styled_df = style_df(matching)
        styled_html = styled_df.to_html()

        download_button = '''
            <a href="/download" class="btn btn-info" style="
                background-color: #0056b3;
                color: white;
                border: none;
                padding: 10px 20px;
                text-align: center;
                text-decoration: none;
                display: inline-block;
                font-size: 16px;
                border-radius: 5px;
                cursor: pointer;
                margin-top: 10px;
            ">
                Download as Excel
            </a>
        '''

        analysis_html = f'<div><p>{analysis}</p></div>'
        custom_css = '<style>.btn-lightblue { background-color: #a7caff; color: black; }</style>'
        full_html_content = custom_css + styled_html + download_button + analysis_html

        return full_html_content

if __name__ == '__main__':
    app.run(host='0.0.0.0', port='7779', debug=False)
