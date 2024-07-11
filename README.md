# InvoiceBankStatementAnalysis

**Description:**

InvoiceBankStatementAnalysis is a tool for matching transactions from invoices within bank statements using Gemini, presented through a Flask web application. Features include OCR integration, transaction matching, data visualization, and a user-friendly web interface. Easy to install, use, and extend. Licensed under MIT.

## Features
- **OCR Integration:** Utilizes Google Cloud Document AI for high-accuracy Optical Character Recognition (OCR) to extract text from bank statements and invoices.
- **Transaction Matching:** Employs advanced algorithms powered by Gemini to analyze and match invoice details with corresponding bank statement transactions.
- **Flask Web Interface:** Provides a user-friendly web interface built with Flask for uploading files, processing data, and displaying results.
- **Data Visualization:** Generates detailed analysis and matching results, with options to download the data as an Excel file.
- **Modular Design:** Code is organized into modular components, making it easy to maintain and extend.

## Installation
1. Clone the repository:
    ```bash
    git clone https://github.com/yourusername/InvoiceBankStatementAnalysis.git
    cd InvoiceBankStatementAnalysis
    ```
2. Create and activate a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```
3. Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4. Set up environment variables:
    - Create a `.env` file and add the necessary credentials and configuration settings as specified in the provided `.env.example`.

## Usage
1. Start the Flask application:
    ```bash
    python app.py
    ```
2. Open your web browser and navigate to `http://localhost:7777`.
3. Upload bank statements and invoices through the web interface.
4. View and download the matching results.

## Contributing
Contributions are welcome! Please fork the repository and submit pull requests for any enhancements or bug fixes.

## License
This project is licensed under the MIT License.
