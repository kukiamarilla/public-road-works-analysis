import sys
import pandas as pd

def preprocess(input_path, output_path):
    df = pd.read_excel(input_path)
    df_filtered = df[pd.to_numeric(df['ID licitación'], errors='coerce').notna()]
    df_filtered.to_csv(output_path, index=False)

if __name__ == "__main__":
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    preprocess(input_path, output_path)