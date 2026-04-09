import urllib.request
import zipfile
import os
import sys

flutter_url = "https://storage.googleapis.com/flutter_infra_release/releases/stable/windows/flutter_windows_3.29.1-stable.zip"
home = os.path.expanduser("~")
zip_path = os.path.join(home, "flutter_sdk.zip")
extract_dir = os.path.join(home, "flutter_python")

print(f"Downloading {flutter_url} to {zip_path}...")
urllib.request.urlretrieve(flutter_url, zip_path)
print("Download complete.")

print(f"Extracting to {extract_dir}...")
os.makedirs(extract_dir, exist_ok=True)
with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    zip_ref.extractall(extract_dir)
print("Extraction complete.")

# Verify flutter.bat exists
bat_path = os.path.join(extract_dir, "flutter", "bin", "flutter.bat")
if os.path.exists(bat_path):
    print(f"SUCCESS: Found flutter.bat at {bat_path}")
else:
    print(f"ERROR: Could not find flutter.bat at {bat_path}")
