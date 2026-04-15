import pandas as pd
import os

def clean_csv(file_path):
    if not os.path.exists(file_path):
        print(f"File {file_path} not found.")
        return

    print(f"Reading {file_path}...")
    df = pd.read_csv(file_path)
    
    initial_count = len(df)
    print(f"Initial row count: {initial_count}")
    
    # Remove duplicates
    df.drop_duplicates(inplace=True)
    after_duplicates = len(df)
    print(f"Rows after removing duplicates: {after_duplicates}")
    
    # Remove nulls
    df.dropna(inplace=True)
    final_count = len(df)
    print(f"Rows after removing nulls: {final_count}")
    
    df.to_csv(file_path, index=False)
    print(f"Successfully cleaned and saved {file_path}.")

if __name__ == "__main__":
    clean_csv('dataset.csv')
