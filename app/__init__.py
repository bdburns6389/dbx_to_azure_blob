from flask import Flask
import logging

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)


from app import routes
