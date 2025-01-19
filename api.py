from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List, Dict, Any
import httpx
import smartsheet

app = FastAPI()
SMARTSHEET_KEY = "5WJCTGhYBqjXx7UeppXrIaSSWASmcp3VqNr6T"
smartsheet_client = smartsheet.Smartsheet(SMARTSHEET_KEY)
CONTACTS_SHEET_ID = "5103766730657668"
EVENTS_SHEET_ID = "2879486383050628"


sheets = {}
response = smartsheet_client.Sheets.list_sheets(include_all=True)  # Call the list_sheets() function and store the response object
for sheet in response.data:
    sheets[sheet.id] = sheet.name


# # Smartsheet API Client Class
# class SmartsheetAPI:
#     def __init__(self, token: str, sheet_id: str):
#         self.base_url = "https://api.smartsheet.com/2.0"
#         self.token = token
#         self.sheet_id = sheet_id
#         self.headers = {"Authorization": f"Bearer {self.token}"}
#
#     async def fetch_row_data(self, row_id: int):
#         url = f"{self.base_url}/sheets/{self.sheet_id}/rows/{row_id}"
#         async with httpx.AsyncClient() as client:
#             response = await client.get(url, headers=self.headers)
#             if response.status_code == 200:
#                 return response.json()
#             else:
#                 raise HTTPException(status_code=response.status_code, detail=response.text)
#
#     async def update_row(self, row_data: Dict[str, Any]):
#         url = f"{self.base_url}/sheets/{self.sheet_id}/rows"
#         async with httpx.AsyncClient() as client:
#             response = await client.put(url, json=row_data, headers=self.headers)
#             if response.status_code != 200:
#                 raise HTTPException(status_code=response.status_code, detail=response.text)

# WhenIWork API Client Class
class WhenIWorkAPI:
    def __init__(self, token: str):
        self.base_url = "https://api.wheniwork.com/2"
        self.token = token
        self.headers = {"Authorization": f"Bearer {self.token}"}

    async def create_or_update_shift(self, shift_data: Dict[str, Any]):
        url = f"{self.base_url}/shifts"
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=shift_data, headers=self.headers)
            if response.status_code not in [200, 201]:
                raise HTTPException(status_code=response.status_code, detail=response.text)

# Instantiate API clients
# smartsheet_client = SmartsheetAPI(token="5WJCTGhYBqjXx7UeppXrIaSSWASmcp3VqNr6T", sheet_id="2879486383050628")
wheniwork_client = WhenIWorkAPI(token="your_wheniwork_token")


# Data model for Smartsheet webhook payload
class SmartsheetCellPayload(BaseModel):
    objectType: str
    eventType: str
    rowId: int
    columnId: int
    userId: int
    timestamp: str

class SmartsheetRowPayload(BaseModel):
    objectType: str
    eventType: str
    id: int
    userId: int
    timestamp: str

# Data model for WhenIWork webhook payload
class WhenIWorkWebhookPayload(BaseModel):
    uuid: str
    type: str
    userId: str
    createdAt: str
    sentAt: str
    data: Dict[str, Any]

MAP_CONTACTS_SMARTSHEET = {
    5103766730657668: {
        "First Name": "id",
        "Last Name": "id",
        "Email": "email",
        "Phone Number": "phone_number",
        "WIW_Position": "positions",
        "WIW_Schedule": "locations",
        "Capabilities": "tags"
    }
}
# Endpoint to receive Smartsheet webhook calls
@app.post("/webhook/smartsheet")
async def handle_smartsheet_webhook(request: Request):
    try:
        payload = await request.json()
        print(payload)
        if 'events' in payload:
            sheet_events = [event for event in payload['events'] if event['objectType'] == 'sheet']
            row_events = [SmartsheetRowPayload(**event) for event in payload['events'] if event['objectType'] == 'row']
            cell_events = [SmartsheetCellPayload(**event) for event in payload['events'] if event['objectType'] == 'cell']
            row_col_mapping = {}

            for row in row_events:

                row_data = smartsheet_client.Sheets.get_row(
                    sheet_id,  # sheet_id
                    row.id,  # row_id
                    exclude=['linkInFromCellDetails', 'linksOutToCellsDetails', 'nonexistentCells'],
                    include=['columns']
                )
                sheet_id = row.sheet_id
                for col in row_data.columns:
                    row_col_mapping[col.id] = col.title.strip()

                # for cell in cell_events:
                #     if cell.rowId == row.id:
                for cell in row_data.cells:
                    for celle in cell_events:
                        if celle.columnId == cell.column_id:
                            wheniwork_col = MAP_CONTACTS_SMARTSHEET[sheet_id][row_col_mapping[cell.column_id]]
                            print(f"Update when I work col: {wheniwork_col}")

        # Process each event in the webhook payload
        # for event in payload.get("events", []):
        #     if event.get("objectType") == "cell":# and event.get("eventType") == "updated":
        #         # continue
        #         cell_event = SmartsheetCellPayload(**event)
        #         await process_smartsheet_cell_event(cell_event)
        #     elif event.get("objectType") == "row":# and event.get("eventType") == "updated":
        #         row_event = SmartsheetRowPayload(**event)
        #         await process_smartsheet_row_event(row_event)

        if "challenge" in payload:
            return {"smartsheetHookResponse": payload["challenge"]}
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def process_smartsheet_cell_event(event: SmartsheetCellPayload):
    """Processes cell updates from Smartsheet webhook and syncs with WhenIWork."""
    print(f"Processing cell event: {event}")
    # Sample 2: Paginate the list
    response = smartsheet_client.Cells.get_cell_history(
            sheet_id,  # sheet_id
            event.rowId,
        event.columnId,  # column_id
        page_size = 2,
        page = 1
    )
    print(response)
    print(response.data)
    # mapped_data = map_smartsheet_to_wheniwork(cells)
    # if mapped_data:
    #     await wheniwork_client.create_or_update_shift(mapped_data)

async def process_smartsheet_row_event(event: SmartsheetRowPayload):
    """Processes row updates from Smartsheet webhook and syncs with WhenIWork."""
    print(f"Processing row event: {event}")
    row_data = smartsheet_client.Sheets.get_row(
                  sheet_id,       # sheet_id
                  event.rowId,        # row_id
                exclude=['linkInFromCellDetails', 'linksOutToCellsDetails', 'nonexistentCells']
                )
    print(row_data)
    cells = row_data.get("cells", [])
    print(cells)
    # mapped_data = map_smartsheet_to_wheniwork(row_data)
    # if mapped_data:
    #     await wheniwork_client.create_or_update_shift(mapped_data)

# Endpoint to receive WhenIWork webhook calls
@app.post("/webhook/wheniwork")
async def handle_wheniwork_webhook(payload: Dict[str, Any]):
    try:
        events = payload.get("events", [])
        for event in events:
            event_data = WhenIWorkWebhookPayload(**event)
            await process_wheniwork_event(event_data)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def process_wheniwork_event(event: WhenIWorkWebhookPayload):
    """Processes updates from WhenIWork webhook and syncs with Smartsheet."""
    print(f"Processing WhenIWork event: {event}")
    shift_data = event.data.get("fields", {})
    mapped_data = map_wheniwork_to_smartsheet(shift_data)
    if mapped_data:
        await smartsheet_client.update_row(mapped_data)

# Mapping functions

def map_smartsheet_to_wheniwork(row_data: Dict[str, Any]) -> Dict[str, Any]:
    """Maps Smartsheet row data to WhenIWork shift data."""
    try:
        return {
            "start_time": row_data["start_time"],
            "end_time": row_data["end_time"],
            "user_id": row_data["user_id"],
            "location_id": row_data["location_id"],
        }
    except KeyError:
        print("Missing required fields in Smartsheet data.")
        return {}

def map_wheniwork_to_smartsheet(shift_data: Dict[str, Any]) -> Dict[str, Any]:
    """Maps WhenIWork shift data to Smartsheet row data."""
    try:
        return {
            "start_time": shift_data.get("startTime"),
            "end_time": shift_data.get("endTime"),
            "user_id": shift_data.get("userId"),
            "location_id": shift_data.get("locationId"),
        }
    except KeyError:
        print("Missing required fields in WhenIWork data.")
        return {}

def initial_sync():
    ### CONTACTS INFO
    sheet = smartsheet_client.Sheets.get_sheet(CONTACTS_SHEET_ID, exclude=["nonexistentCells"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
    initial_sync()
