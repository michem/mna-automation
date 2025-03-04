import datetime
import json
import os
from pathlib import Path
from typing import List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import (
    MediaFileUpload,
    MediaInMemoryUpload,
    MediaIoBaseDownload,
)

SCOPES = ["https://www.googleapis.com/auth/drive"]
import tempfile


def find_file_by_name(service, file_name, parent_folder_id=None):
    """
    Find a file in Google Drive by name, optionally within a specific folder.
    Returns the file ID if found, None otherwise.
    """
    query = f"name = '{file_name}' and trashed = false"
    if parent_folder_id:
        query += f" and '{parent_folder_id}' in parents"

    results = (
        service.files()
        .list(q=query, spaces="drive", fields="files(id, name)")
        .execute()
    )

    items = results.get("files", [])
    return items[0]["id"] if items else None


def download_file_from_drive(service, file_id, local_path=None):
    """
    Download a file from Google Drive by its ID.
    If local_path is not provided, a temporary file will be created.
    Returns the path to the downloaded file.
    """
    if not local_path:

        file_metadata = service.files().get(fileId=file_id, fields="name").execute()
        file_name = file_metadata.get("name", "downloaded_file")
        _, file_extension = os.path.splitext(file_name)

        temp_file = tempfile.NamedTemporaryFile(suffix=file_extension, delete=False)
        local_path = temp_file.name
        temp_file.close()

    request = service.files().get_media(fileId=file_id)

    with open(local_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()

    return local_path


def get_file_from_drive(file_path):
    """
    Get a file from Google Drive based on the logical path structure.
    Returns the path to the downloaded local file.
    """
    folders = initialize_drive()
    service = folders["service"]

    folder_id, file_name = get_drive_path(file_path)

    file_id = find_file_by_name(service, file_name, folder_id)

    if not file_id:
        raise FileNotFoundError(f"File {file_name} not found in Google Drive")

    local_path = download_file_from_drive(service, file_id)

    return local_path


def read_from_drive(file_path):
    """
    Read a file's content from Google Drive.
    Returns the file content as a string.
    """
    local_path = get_file_from_drive(file_path)

    with open(local_path, "r", encoding="utf-8") as f:
        content = f.read()

    os.unlink(local_path)

    return content


def get_credentials() -> Credentials:
    """Get and refresh Google Drive API credentials."""
    creds = None

    if os.path.exists("token.json"):
        with open("token.json", "r") as token:
            creds = Credentials.from_authorized_user_info(json.load(token))

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:

            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return creds


def create_drive_service():
    """Create and return a Google Drive API service."""
    creds = get_credentials()
    return build("drive", "v3", credentials=creds)


def ensure_folder_exists(
    service, folder_name: str, parent_id: Optional[str] = None
) -> str:
    """
    Ensure a folder exists in Google Drive, creating it if necessary.
    Returns the folder ID.
    """

    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    results = (
        service.files()
        .list(q=query, spaces="drive", fields="files(id, name)")
        .execute()
    )
    items = results.get("files", [])

    if items:
        return items[0]["id"]

    folder_metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }

    if parent_id:
        folder_metadata["parents"] = [parent_id]

    folder = service.files().create(body=folder_metadata, fields="id").execute()
    return folder.get("id")


def upload_file_to_drive(service, file_path: str, folder_id: str) -> str:
    """
    Upload a file to Google Drive in the specified folder.
    Returns the file ID.
    """

    file_name = os.path.basename(file_path)
    mime_type = "text/plain"

    if file_path.endswith(".json"):
        mime_type = "application/json"
    elif file_path.endswith(".md"):
        mime_type = "text/markdown"

    file_metadata = {"name": file_name, "parents": [folder_id]}

    media = MediaFileUpload(file_path, mimetype=mime_type)

    file = (
        service.files()
        .create(body=file_metadata, media_body=media, fields="id")
        .execute()
    )

    return file.get("id")


def upload_string_to_drive(
    service, content: str, file_name: str, folder_id: str, mime_type: str = "text/plain"
) -> str:
    """
    Upload a string directly to Google Drive in the specified folder.
    Returns the file ID.
    """

    file_metadata = {"name": file_name, "parents": [folder_id]}

    media = MediaInMemoryUpload(content.encode("utf-8"), mimetype=mime_type)

    file = (
        service.files()
        .create(body=file_metadata, media_body=media, fields="id")
        .execute()
    )

    return file.get("id")


def setup_drive_folders() -> dict:
    """
    Set up the folder structure in Google Drive.
    Returns a dictionary with folder IDs.
    """
    service = create_drive_service()

    mna_folder_id = ensure_folder_exists(service, "mna_outputs")

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_folder_name = f"outputs_{timestamp}"
    run_folder_id = ensure_folder_exists(service, run_folder_name, mna_folder_id)

    fmp_folder_id = ensure_folder_exists(service, "fmp_data", run_folder_id)

    return {
        "service": service,
        "mna_folder_id": mna_folder_id,
        "run_folder_id": run_folder_id,
        "fmp_folder_id": fmp_folder_id,
        "run_folder_name": run_folder_name,
    }


drive_folders = None


def initialize_drive():
    """Initialize Google Drive folders and return the folder structure."""
    global drive_folders
    if drive_folders is None:
        drive_folders = setup_drive_folders()
    return drive_folders


def get_drive_path(local_path: str) -> tuple:
    """
    Determine the appropriate Google Drive folder for a given local path.
    Returns a tuple of (folder_id, file_name).
    """
    folders = initialize_drive()

    local_path = Path(local_path)
    file_name = local_path.name

    if "fmp_data" in str(local_path):
        return folders["fmp_folder_id"], file_name
    else:
        return folders["run_folder_id"], file_name


def save_to_drive(content: str, file_path: str, mime_type: str = None) -> str:
    """
    Save content to Google Drive.
    Returns the Google Drive file URL.
    """
    folders = initialize_drive()
    service = folders["service"]

    folder_id, file_name = get_drive_path(file_path)

    if not mime_type:
        if file_path.endswith(".json"):
            mime_type = "application/json"
        elif file_path.endswith(".md"):
            mime_type = "text/markdown"
        else:
            mime_type = "text/plain"

    file_id = upload_string_to_drive(service, content, file_name, folder_id, mime_type)

    return f"File saved to Google Drive: mna_outputs/{folders['run_folder_name']}/{file_name} (ID: {file_id})"


def get_drive_file_url(file_id: str) -> str:
    """Generate a shareable URL for a Google Drive file."""
    return f"https://drive.google.com/file/d/{file_id}/view"
