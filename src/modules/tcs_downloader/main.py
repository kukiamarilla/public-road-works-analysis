from tcs_downloader import *
import sys

if __name__ == "__main__":
    tender_id = sys.argv[1]
    output_path = sys.argv[2]
    TCSDownloader().process_tender_documents(tender_id, output_path)