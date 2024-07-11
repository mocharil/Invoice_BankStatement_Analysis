from google.cloud import documentai_v1 as documentai
from google.oauth2 import service_account
from datetime import datetime
import json

class OCRProcessor:
    def __init__(self, credentials_file_path: str):
        with open(credentials_file_path, "r") as creds:
            service_account_info = json.load(creds)
        self.credentials = service_account.Credentials.from_service_account_info(service_account_info)

    def process_ocr(self, project_id: str, location: str, processor_id: str, file_content: bytes, mime_type: str) -> str:
        start = datetime.now()
        opts = {"api_endpoint": f"{location}-documentai.googleapis.com"}
        documentai_client = documentai.DocumentProcessorServiceClient(client_options=opts, credentials=self.credentials)
        resource_name = documentai_client.processor_path(project_id, location, processor_id)
        raw_document = documentai.RawDocument(content=file_content, mime_type=mime_type)
        request = documentai.ProcessRequest(name=resource_name, raw_document=raw_document)
        result = documentai_client.process_document(request=request).document
        print('Done in', (datetime.now() - start).total_seconds())
        return result.text
