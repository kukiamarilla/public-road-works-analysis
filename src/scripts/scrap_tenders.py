from pathlib import Path
import requests
import sys
import pandas as pd

src_dir = Path(__file__).parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from modules.pdf_reader import PDFReader
from modules.tcs_downloader import TCSDownloader

def get_tenderers_number(tender_id):
    try:
        response = requests.get(f"https://www.contrataciones.gov.py/datos/api/v3/doc/tender/{tender_id}")
        tender = response.json()
        return int(tender["tender"]["numberOfTenderers"])
    except Exception as e:
        print("No se pudo obtener la cantidad de oferentes")
        raise e

def download_pbc(tender_id):
    try:
        downloader = TCSDownloader()
        return downloader.process_tender_documents(tender_id, "./tmp")
    except Exception as e:
        print("No se pudo obtener el pbc")
        raise e


def extract_pbc_text(tender_file):
    try:
        reader = PDFReader(tender_file)
        return reader.read_pdf_as_markdown()
    except Exception as e:
        print("No se pudo extraer el texto del pbc")
        raise e

def scrap_pbcs(ids):
    tenderers_numbers = []
    success_extracted = []
    for idx, id in enumerate(ids):
        print(f"Extrayendo licitación {idx + 1} de {len(ids)}, con id {id}")
        try:
            filename = download_pbc(id)
            text_pbc = extract_pbc_text(filename)
            tenderers_number = get_tenderers_number(id)
            print("Extraido")
        except:
            continue
        success_extracted.append(id)
        tenderers_numbers.append(tenderers_number)
        output = open(f"./data/pbcs_extracted/{id}.txt", "w+")
        output.write(text_pbc)
        output.close()
    df = pd.DataFrame({"Id llamado": success_extracted, "Cantidad de oferentes": tenderers_numbers})
    df.to_csv("./data/dataset.csv", index=False)

if __name__ == "__main__":
    ids_file = open("./data/ids.txt")
    ids = ids_file.read().split(" ")
    scrap_pbcs(ids[5:10])