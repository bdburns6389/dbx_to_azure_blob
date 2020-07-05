from app import app
import dropbox
import os
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient

dbx_access_token = os.environ["DROPBOX_ACCESS_TOKEN"]
azure_conn_string = os.environ["AZURE_CONN_STRING"]
azure_container_name = os.environ["AZURE_CONTAINER_NAME"]


@app.route("/")
@app.route("/index")
def index():

    dbx = dropbox.Dropbox(dbx_access_token)

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

            file = dbx.files_download(filename)
            path_name = file[0].path_lower

            new_filename = filename.strip("/")
            content = file[1].content

            # Write dropbox file to new location.
            upload_to_blob_storage(filename=new_filename, file_content=content)

        cursor = result.cursor
        has_more = result.has_more
        write_cursor(cursor)

    return cursor


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
