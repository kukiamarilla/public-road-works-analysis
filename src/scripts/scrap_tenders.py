from pathlib import Path
import requests
import sys
import os
import json
import pandas as pd

src_dir = Path(__file__).parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from modules.pdf_reader import PDFReader
from modules.tcs_downloader import TCSDownloader

CHECKPOINT_FILE = "./data/checkpoint.json"
DATASET_FILE = "./data/dataset.csv"

def load_checkpoint():
    """Load checkpoint with processed IDs and failed IDs."""
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as f:
            return json.load(f)
    return {"processed": [], "failed": []}

def save_checkpoint(checkpoint):
    """Save checkpoint to file."""
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(checkpoint, f, indent=2)

def append_to_dataset(tender_id, tenderers_number):
    """Append a single record to the dataset CSV."""
    new_row = pd.DataFrame({"Id llamado": [tender_id], "Cantidad de oferentes": [tenderers_number]})
    
    if os.path.exists(DATASET_FILE):
        existing_df = pd.read_csv(DATASET_FILE)
        df = pd.concat([existing_df, new_row], ignore_index=True)
    else:
        df = new_row
    
    df.to_csv(DATASET_FILE, index=False)

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
    checkpoint = load_checkpoint()
    processed_ids = set(checkpoint["processed"])
    failed_ids = set(checkpoint["failed"])
    
    # Filter out already processed IDs
    pending_ids = [id for id in ids if id not in processed_ids]
    
    if len(pending_ids) < len(ids):
        print(f"Resumiendo desde checkpoint: {len(processed_ids)} ya procesados, {len(pending_ids)} pendientes")
    
    for idx, id in enumerate(pending_ids):
        print(f"Extrayendo licitación {idx + 1} de {len(pending_ids)}, con id {id}")
        try:
            filename = download_pbc(id)
            text_pbc = extract_pbc_text(filename)
            tenderers_number = get_tenderers_number(id)
            
            # Save extracted text
            output_path = f"./data/pbcs_extracted/{id}.txt"
            with open(output_path, "w+") as output:
                output.write(text_pbc)
            
            # Append to dataset immediately
            append_to_dataset(id, tenderers_number)
            
            # Update checkpoint as processed
            checkpoint["processed"].append(id)
            if id in failed_ids:
                checkpoint["failed"].remove(id)
            save_checkpoint(checkpoint)
            
            print(f"Extraido y guardado: {id}")
            
        except KeyboardInterrupt:
            print("\nInterrupción detectada. Progreso guardado en checkpoint.")
            save_checkpoint(checkpoint)
            sys.exit(0)
        except Exception as e:
            print(f"Error procesando {id}: {e}")
            if id not in failed_ids:
                checkpoint["failed"].append(id)
                save_checkpoint(checkpoint)
            continue
    
    print(f"\nProceso completado. Total procesados: {len(checkpoint['processed'])}, Fallidos: {len(checkpoint['failed'])}")

if __name__ == "__main__":
    ids_file = open("./data/ids.txt")
    ids = ids_file.read().split(" ")
    scrap_pbcs(ids)