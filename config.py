import os
from dotenv import load_dotenv
load_dotenv()

SPREADSHEET_KEY = os.getenv('SPREADSHEET_KEY')
NODE_ID = os.getenv('NODE_ID')
USER_ID = os.getenv('USER_ID')
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
