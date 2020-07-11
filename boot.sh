#!/bin/sh
source venv/bin/activate
exec gunicorn -b :5000 --access-logfile - --error-logfile - dbx_to_azure_blob:dbx_to_azure_blob