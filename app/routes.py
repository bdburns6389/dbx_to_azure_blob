from app import app
import dropbox
from flask import request, Response
import os
from hashlib import sha256
import hmac
import threading
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from dotenv import load_dotenv

APP_ROOT = os.path.join(os.path.dirname(__file__), "..")
dotenv_path = os.path.join(APP_ROOT, ".env")
load_dotenv(dotenv_path)

dbx_access_token = os.getenv("DROPBOX_ACCESS_TOKEN")
azure_conn_string = os.getenv("AZURE_CONN_STRING")
azure_container_name = os.getenv("AZURE_CONTAINER_NAME")


@app.route("/webhook", methods=["GET"])
def verify():
    """Respond to the webhook verification (GET request) by echoing back the challenge parameter."""
    resp = Response(request.args.get("challenge"))
    resp.headers["Content-Type"] = "text/plain"
    resp.headers["X-Content-Type-Options"] = "nosniff"

    return resp


@app.route("/webhook", methods=["POST"])
def index():
    dbx = dropbox.Dropbox(dbx_access_token)
    app.logger.info("post caction hit")
    app.logger.info(f'DBX: {dbx_access_token}')
    app.logger.info(f'AZ Conn: {azure_conn_string}')
    app.logger.info(f'AZ Contain: {azure_container_name}')

    # Get cursor from local file. If it doesn't exist, hit the API to get latest cursor.
    cursor = read_cursor()
    if not cursor.strip():
        latest_cursor = dbx.files_list_folder_get_latest_cursor("", recursive=True)
        cursor = latest_cursor.cursor
        write_cursor(cursor)

    has_more = True
    while has_more:
        result = dbx.files_list_folder_continue(cursor)

        for entry in result.entries:
            filename = entry.path_lower
            app.logger.info(f'Filename: {filename}')

            file = dbx.files_download(filename)
            path_name = file[0].path_lower

            new_filename = filename.strip("/")
            content = file[1].content

            # Write dropbox file to new location.
            upload_to_blob_storage(filename=new_filename, file_content=content)

        cursor = result.cursor
        has_more = result.has_more
        write_cursor(cursor)

    return ""


def upload_to_blob_storage(filename, file_content):
    blob_service_client = BlobServiceClient.from_connection_string(azure_conn_string)

    blob_client = blob_service_client.get_blob_client(
        container=azure_container_name, blob=filename
    )

    blob_client.upload_blob(file_content, overwrite=True)


def read_cursor():
    if not os.path.exists("cursor.txt"):
        f = open("cursor.txt", "w")
        f.write(" ")
        f.close()

    file = open("cursor.txt", "r")
    cursor = file.read()
    file.close()
    return cursor


def write_cursor(cursor):
    file = open("cursor.txt", "w")
    file.write(cursor)
    file.close()
