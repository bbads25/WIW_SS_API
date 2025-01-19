from api import smartsheet_client
from controllers.sync_manager import SyncManager
from typing import Dict, Any

import threading
import uvicorn
from fastapi import FastAPI, HTTPException, Request

from models.SmartsheetEvent import SmartsheetEvent
from models.WhenIWorkEvent import WhenIWorkEvent
from controllers.wiw import WhenIWork
from controllers.sheet import Smartsheet

app = FastAPI()
wiw = WhenIWork()
smartsheet_webhook_url = "https://da8a-2-49-134-21.ngrok-free.app/webhook/smartsheet"
smartsheet = Smartsheet()
manager = SyncManager(wiw, smartsheet)

# Endpoint to receive Smartsheet webhook calls
@app.post("/webhook/wheniwork")
async def handle_wheniwork_webhook(request: Request):
    try:
        payload = await request.json()
        events = payload.get("events", [])
        print("Events recieved from wheniwork: ")
        print(events)
        for event in events:
            print("Processing event uuid: ", event["uuid"])
            event_data = WhenIWorkEvent(**event)
            manager.sync_wiw_to_smartsheet(event_data)
            print("Event processed uuid: ", event_data.uuid)
        return {"success": True}
    except Exception as e:
        print("Error handling whenIwork event")
        print(e)
        return {"success": False, "error": str(e)}


@app.post("/webhook/smartsheet")
async def handle_smartsheet_webhook(request: Request):
    try:
        payload = await request.json()
        print(payload)
        for event in payload.get("events", []):
            print("Processing event: ", event)
            event_data = SmartsheetEvent(**event)
            manager.sync_smartsheet_to_wiw(event_data)

        if "challenge" in payload:
            return {"smartsheetHookResponse": payload["challenge"]}
        return {"success": True}
    except Exception as e:
        print("Error handling smartsheet event")
        print(e)
        return {"success": False, "error": str(e)}

@app.get("/")
async def root():
    return "YALLA HURRRRR"

def start_server():
    uvicorn.run(app, host="0.0.0.0", port=3000)


if __name__ == '__main__':
    # uvicorn.run(app, host='0.0.0.0', port=3000)
    # Start server in a separate thread
    server_thread = threading.Thread(target=start_server)
    server_thread.start()

    print("Setting up smartsheet webhook")
    smartsheet.initialize_webhook(smartsheet_webhook_url)