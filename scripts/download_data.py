import os
import subprocess

DATA_DIR = r"C:\Projects\continuous-keystroke-auth\data"
FREE_TEXT_URL = "https://zenodo.org/api/records/7886743/files/free-text.csv/content"
DEMOGRAPHICS_URL = "https://zenodo.org/api/records/7886743/files/demographics.csv/content"

def download_file_curl(url, filename):
    filepath = os.path.join(DATA_DIR, filename)
    if os.path.exists(filepath):
        print(f"{filename} already exists at {filepath}. Skipping download.")
        return filepath
    
    print(f"Downloading {filename} from {url} using curl.exe...")
    cmd = ["curl.exe", "-L", "-o", filepath, url]
    try:
        result = subprocess.run(cmd, check=True)
        print(f"Successfully downloaded {filename} to {filepath}\n")
    except subprocess.CalledProcessError as e:
        print(f"Failed to download {filename} with curl: {e}")
        raise e
    return filepath

if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    download_file_curl(FREE_TEXT_URL, "free-text.csv")
    download_file_curl(DEMOGRAPHICS_URL, "demographics.csv")
