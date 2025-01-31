# 
import requests
import os

# Define the CashCtrl API credentials and URL
CASHCTRL_API_URL = "https://myorg.cashctrl.com/api/v1"
API_KEY = "zjdqcZjsfSYyM4EPG19tHss6X5NIHf0b:"  # Replace with your actual API key

# Prepare the files
files_to_upload = [
    {"file_path": "report.pdf", "mime_type": "application/pdf"},
    {"file_path": "image.png", "mime_type": "image/png"}
]

# Step 1: Prepare the upload by informing the API of the files' names and mime types
def prepare_upload(files):
    files_data = [{"name": file["file_path"], "mimeType": file["mime_type"]} for file in files]
    url = f"{CASHCTRL_API_URL}/file/prepare.json"
    response = requests.post(url, auth=(API_KEY, ""), data={"files": files_data})

    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            return data["data"]
        else:
            print("Error preparing files:", data)
            return None
    else:
        print("Failed to prepare upload:", response.status_code)
        return None

# Step 2: Upload the files using the provided URLs from Step 1
def upload_files(files, prepared_files):
    for i, file in enumerate(files):
        prepared_file = prepared_files[i]
        write_url = prepared_file["writeUrl"]
        
        # Open the file and upload it
        with open(file["file_path"], "rb") as f:
            response = requests.put(write_url, data=f)
            if response.status_code == 200:
                print(f"Successfully uploaded {file['file_path']}")
            else:
                print(f"Failed to upload {file['file_path']}: {response.status_code}")

# Step 3: Persist the uploaded files
def persist_files(file_ids):
    url = f"{CASHCTRL_API_URL}/file/persist.json"
    data = {"ids": ",".join(map(str, file_ids))}
    response = requests.post(url, auth=(API_KEY, ""), data=data)

    if response.status_code == 200:
        print("Successfully persisted the files.")
    else:
        print("Failed to persist files:", response.status_code)

# Step 4: Optionally, add description or additional information to the files
def create_files_with_info(file_data):
    for file in file_data:
        url = f"{CASHCTRL_API_URL}/file/create.json"
        data = {
            "id": file["fileId"],
            "name": file["name"],
            "description": file.get("description", ""),
            "notes": file.get("notes", "")
        }
        response = requests.post(url, auth=(API_KEY, ""), data=data)

        if response.status_code == 200:
            print(f"Successfully created file {file['name']} with additional info.")
        else:
            print(f"Failed to create file {file['name']} with additional info:", response.status_code)

# Main function to handle the upload process
def upload_and_persist_files():
    # Step 1: Prepare files
    prepared_files = prepare_upload(files_to_upload)
    if prepared_files:
        file_ids = [file["fileId"] for file in prepared_files]

        # Step 2: Upload files
        upload_files(files_to_upload, prepared_files)

        # Step 3: Persist the uploaded files
        persist_files(file_ids)

        # Optional: Step 4, create files with additional info (e.g., description)
        file_info = [{"fileId": file_id, "name": file["file_path"], "description": "Uploaded via API"} 
                     for file_id, file in zip(file_ids, files_to_upload)]
        create_files_with_info(file_info)

if __name__ == "__main__":
    upload_and_persist_files()
