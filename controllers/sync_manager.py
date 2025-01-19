from os import cpu_count

from api import response, sheet
from controllers.sheet import Smartsheet
from models.SmartsheetEvent import SmartsheetEvent
from models.WhenIWorkEvent import WhenIWorkEvent
from transformers.data_transformer import DataTransformer
from controllers.wiw import WhenIWork


class SyncManager:
    def __init__(self, wiw: WhenIWork, smartsheet: Smartsheet):
        self.wiw = wiw
        self.smartsheet = smartsheet
        pass

    def sync_wiw_to_smartsheet(self, event: WhenIWorkEvent):
        print("Event data: ", event.data)
        if "users" in event.type:
            sheet_id = self.smartsheet.CONTACTS_SHEET_ID
        else:
            sheet_id = self.smartsheet.CONTACTS_SHEET_ID

        if event.type == "users::created" or event.type == "users::updated":
            print("Event Type: ", event.type)
            user_id = event.data['userId']
            wiw_data = self.wiw.get_user(user_id)
            user_tags = self.wiw.get_user_tags(user_id)
            print("User data from wiw: ", wiw_data)
            smartsheet_data = DataTransformer.wiw_to_smartsheet_contact(wiw_data, user_tags, self.wiw)
            print("Smartsheet data transformed: ", smartsheet_data)

            response = self.smartsheet.create_or_update_row(sheet_id, smartsheet_data)
            print("Final response: ", response)
            print("Event Processed!")
        elif event.type == "users::deleted":
            # Do nothing on wiw deletion
            pass

    def sync_smartsheet_to_wiw(self, event: SmartsheetEvent):
        print("Smartsheet Event data: ", event.eventType, ' ', event.objectType)
        sheet_id = self.smartsheet.CONTACTS_SHEET_ID
        if event.objectType == 'sheet':
            pass
        elif event.objectType == 'row':
            print("Event Type: ", event.eventType)
            print("Object Type: ", event.objectType)
            rowId = event.id
            row, columns = self.smartsheet.get_row(sheet_id, rowId)
            primary_column_id = next((key for key, value in columns.items() if value == 'Primary Column'), None)
            print("Primary Column ID: ", primary_column_id)
            contact = {}
            for cell in row.cells:
                if columns[cell.column_id] in self.smartsheet.CONTACT_SHEET_COLUMNS:
                    contact[columns[cell.column_id]] = cell.value
            # contact = {'Name': 'Doryan Sparkman', 'Email': 'doryansparkman@yahoo.com', 'Phone Number': '(404) 944-9611', 'Capabilities': 'Baseball, Hockey, Basketball (2D)', 'First Name': 'Doryan', 'Last Name': 'Sparkman', 'WIW_Position': 'Operator, Supervisor', 'WIW_Schedule': 'Default'}
            contact = DataTransformer.smartsheet_to_wiw_contact(contact)
            # Updating user in wiw
            name = f"{contact['first_name']} {contact['last_name']}"
            if contact['id'] != '':
                r = self.wiw.create_or_update_user(contact, user_id=contact['id'])
            else:
                user = self.wiw.get_users(name)
                if user and len(user['users']) > 0:
                    # user exists in wiw so update it
                    print(f"User {name} {user['users'][0]['id']} already exists, updating...")
                    r = self.wiw.create_or_update_user(contact, user_id=user['users'][0]['id'])
                else:
                    print(f"User {name} does not exist, creating...")
                    r = self.wiw.create_or_update_user(contact)

            if not r:
                print(f'Error processing user {name}')
                return None
            else:
                print(f"User {name} processed!\n")
                print(r)
                # if no id in smartsheet, add id to smartsheet
                if contact['id'] == '':
                    self.smartsheet.update_cell(sheet_id, rowId, primary_column_id, r['id'])

                return r

        elif event.objectType == 'cell':
            rowId = event.rowId
            columnId = event.columnId
            recent_value = self.smartsheet.get_cell_history(sheet_id, rowId, columnId)[0].display_value
            column_updated = self.smartsheet.get_column_name(sheet_id, columnId)
            updated_cell = {column_updated: recent_value}
            print("Cell Event Recieved: ", updated_cell)

# {'events': [{'uuid': '70c354f2-0100-41fb-b81e-0f133c65f561', 'type': 'users::updated', 'userId': '50757204', 'createdAt': '2025-01-16T11:13:05.314999103Z', 'sentAt': '2025-01-16T11:13:06.315Z', 'data': {'fields': {'lastName': {'new': 'Ric', 'old': 'Ricee'}}, 'userId': '51136971'}}]}
# INFO:     18.213.164.31:0 - "POST /webhook/wheniwork HTTP/1.1" 200 OK
# {'events': [{'uuid': '4bbc1b26-d085-4dcb-ba9e-c710f20a6f26', 'type': 'shifts::created', 'userId': '50757204', 'createdAt': '2025-01-16T11:15:39.596328973Z', 'sentAt': '2025-01-16T11:15:40.597Z', 'data': {'fields': {'accountId': {'new': 4036145, 'old': None}, 'breakTime': {'new': 1, 'old': None}, 'color': {'new': 'cccccc', 'old': None}, 'creatorId': {'new': 50757204, 'old': None}, 'endTime': {'new': '2025-01-14 14:00:00', 'old': None}, 'instances': {'new': 1, 'old': None}, 'locationId': {'new': 5640122, 'old': None}, 'positionId': {'new': 11222535, 'old': None}, 'published': {'new': 1, 'old': None}, 'publishedDate': {'new': '2025-01-16 11:15:39', 'old': None}, 'siteId': {'new': 5286093, 'old': None}, 'startTime': {'new': '2025-01-13 14:00:00', 'old': None}}, 'shiftId': '3473997896'}}]}
# INFO:     52.3.78.100:0 - "POST /webhook/wheniwork HTTP/1.1" 200 OK
# {'events': [{'uuid': '109ea4b3-adb0-4c96-ba66-f03bcc602b75', 'type': 'shifts::updated', 'userId': '50757204', 'createdAt': '2025-01-16T11:15:40.246176004Z', 'sentAt': '2025-01-16T11:15:41.247Z', 'data': {'fields': {'notifiedAt': {'new': '2025-01-16 11:15:40', 'old': '0000-00-00 00:00:00'}}, 'shiftId': '3473997896'}}]}
# INFO:     52.3.78.100:0 - "POST /webhook/wheniwork HTTP/1.1" 200 OK
# {'
# {'fields': {'role': {'new': 3, 'old': 5}}, 'userId': '51136970'}
