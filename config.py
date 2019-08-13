import json

with open("config.json") as f:
    config = json.load(f)

REMOTE_SELENIUM_URL = config.get("REMOTE_SELENIUM_URL", "http://localhost:4444/wd/hub")
OPENBANK_USER_ID_TYPE = config["OPENBANK_USER_ID_TYPE"]
OPENBANK_USER_ID = config["OPENBANK_USER_ID"]
OPENBANK_USER_PASSWORD = config["OPENBANK_USER_PASSWORD"]
OPENBANK_CONTRACT_NUMBER = config["OPENBANK_CONTRACT_NUMBER"]
