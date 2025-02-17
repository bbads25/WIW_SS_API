import os
import time
import traceback

import requests

from controllers.sync_manager import SyncManager
import threading
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from contextlib import asynccontextmanager

from models.SmartsheetEvent import SmartsheetEvent
from models.WhenIWorkEvent import WhenIWorkEvent
from controllers.wiw import WhenIWork
from controllers.sheet import Smartsheet

print("PROD" if os.environ["PRODUCTION"]==1 else "DEV")
wiw = WhenIWork()
smartsheet_webhook_url = "https://heptic.ae/webhook/smartsheet" if os.environ["PRODUCTION"] == 1 else "https://2d80-2-49-134-21.ngrok-free.app/webhook/smartsheet"
smartsheet = Smartsheet()
manager = SyncManager(wiw, smartsheet)
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     print("Server has started, initializing Smartsheet webhook...")
#     smartsheet.initialize_webhook(smartsheet_webhook_url)
#     yield
#     # Cleanup if needed below

app = FastAPI()


def wait_for_server_ready(url, timeout=30):
    """Poll the server until it's ready to accept requests"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                print("Server is ready!")
                return True
        except requests.exceptions.ConnectionError:
            pass  # Server is not up yet

        time.sleep(1)  # Wait before retrying

    print("Error: Server did not start within the timeout period.")
    return False


# Endpoint to receive Smartsheet webhook calls
@app.post("/webhook/wheniwork")
async def handle_wheniwork_webhook(request: Request):
    try:
        payload = await request.json()
        events = payload.get("events", [])
        print("Events recieved from wheniwork: ")
        print(events)
        # for event in events:
        #     print("Processing event uuid: ", event["uuid"])
        #     event_data = WhenIWorkEvent(**event)
        #     manager.sync_wiw_to_smartsheet(event_data)
        #     print("Event processed uuid: ", event_data.uuid)
        return {"success": True}
    except Exception as e:
        print("Error handling whenIwork event")
        print(traceback.print_exc())
        return {"success": False, "error": str(e)}


@app.post("/webhook/smartsheet")
async def handle_smartsheet_webhook(request: Request):
    try:
        payload = await request.json()
        print(payload)
        sheet_id = payload.get("scopeObjectId", "")
        for event in payload.get("events", []):
            print("Processing event: ", event)
            event_data = SmartsheetEvent(**event)
            manager.sync_smartsheet_to_wiw(sheet_id, event_data)

        if "challenge" in payload:
            return {"smartsheetHookResponse": payload["challenge"]}
        return {"success": True}
    except Exception as e:
        print("Error handling smartsheet event")
        print(e)
        return {"success": False, "error": str(e)}

@app.get("/")
async def root():
    return {"status": "YALLA HURRRR"}

def start_server():
    uvicorn.run(app, host="0.0.0.0", port=3000)


if __name__ == '__main__':
    # uvicorn.run(app, host='0.0.0.0', port=3000)
    # Start server in a separate thread
    server_thread = threading.Thread(target=start_server)
    server_thread.start()
    # Wait for the server to be ready
    server_url = "http://127.0.0.1:3000/"
    if wait_for_server_ready(server_url):
        smartsheet.initialize_webhook(smartsheet_webhook_url)
