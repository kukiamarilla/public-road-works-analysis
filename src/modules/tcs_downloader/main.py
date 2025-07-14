from tcs_downloader import *
import json
if __name__ == "__main__":
    tender_id = "361490"
    document_list = TCSDownloader().get_document_list(tender_id)
    selected_document = TCSDownloader().select_document(document_list)
    print(selected_document)