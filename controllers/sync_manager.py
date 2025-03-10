from contacts_sheet import sheet_id
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
        elif "sites" in event.type:
            sheet_id = self.smartsheet.JOB_SITES_SHEET_ID

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

    def sync_smartsheet_to_wiw(self, sheet_id, event: SmartsheetEvent):
        # print("Smartsheet Event data: ", event.eventType, ' ', event.objectType, ' ', sheet_id)
        if sheet_id == self.smartsheet.CONTACTS_SHEET_ID:
            print("Processing contacts sheet event")
            self.smartsheet_contacts_event(sheet_id, event)
        elif sheet_id == self.smartsheet.JOB_SITES_SHEET_ID:
            print("Processing job sites sheet event")
            self.smartsheet_job_sites_event(sheet_id, event)
        elif sheet_id == self.smartsheet.EVENTS_SHEET_ID:
            print("Processing events sheet event")
            self.smartsheet_events_event(sheet_id, event)


    def smartsheet_events_event(self, sheet_id, event):
        if event.objectType == "sheet":
            pass
        if event.objectType == "row":
            rowId = event.id
            print("Processing row event: ", rowId)
            row, columns = self.smartsheet.get_row(sheet_id, rowId)
            primary_column_id = next((key for key, value in columns.items() if value == 'Primary Column'), None)
            e = {}
            for cell in row.cells:
                if columns[cell.column_id] in self.smartsheet.EVENTS_SHEET_COLUMNS:
                    e[columns[cell.column_id]] = cell.value
            print('initial:', e) # good enough

            client_team_lookup = self.smartsheet.master_lookup(e['Client Team'])
            locations = ""
            positions = ""
            if client_team_lookup:
                locations = client_team_lookup['WIW_Schedule']
                positions = client_team_lookup['WIW_Position']
            else:
                locations = "Default"
                positions = "Operator"
            print("Client team lookup: ", client_team_lookup)
            print("Selected location: ", locations)
            locations = self.wiw.get_locations(locations)
            if locations[0]['name'].lower() != client_team_lookup['WIW_Schedule'].lower():
                location_id = self.wiw.create_location(client_team_lookup['WIW_Schedule'])
                e['location_id'] = location_id
            else:
                e['location_id'] = locations[0]['id'] if locations else ""

            print("response locations: ", locations)
            positions = self.wiw.get_positions(positions)
            e['position_id'] = positions[0]['id'] if positions else ""
            site = self.wiw.get_sites(e['Operating Site'])
            if not site:
                site = self.wiw.create_or_update_job_site({"id": "", "name": e['Operating Site'], "address": ""})
            print("SITE FOUND/CREATED:", site)
            e['site_id'] = site['id'] if site else ""
            # TODO: client_team_lookup['Capability_Required']
            # TODO: client_team_lookup['WIW_Shift_Task_Lists']
            print('intermediate: ', e)

            users = e['Operator'].split(', ') if 'Operator' in e and e['Operator'] != '' and e['Operator'] else ["0"]
            user_ids = []
            for user in users:
                if user == "0":
                    user_ids.append(user)
                    continue
                wiw_user = self.wiw.get_users(user)
                if wiw_user and len(wiw_user['users']) > 0:
                    wiw_user = wiw_user['users'][0]['id']
                    user_ids.append(wiw_user)
                else:
                    print(f"User does not exist in wiw, creating {user}...")
                    contact = DataTransformer.smartsheet_to_wiw_contact({"First Name": user.split(' ')[0], "Last Name": user.split(' ')[-1]})
                    user = self.wiw.create_or_update_user(contact)
                    user_ids.append(user['id'])

            shift_ids = []
            for user_id in user_ids:
                print("Processing user: ", user_id)
                shift = DataTransformer.smartsheet_to_wiw_shift(e, user_id)
                print('FINAL SHIFT: ', shift)
                r = self.wiw.create_or_update_shift(shift)
                if r:
                    print("Shift created: ", r)
                    shift_ids.append(r['id'])
            if shift_ids:
                print("Publishing shifts: ", shift_ids)
                return self.wiw.publish_shifts(shift_ids)
            else:
                print("No shifts published!")
                return False
        if event.objectType == "cell":
            pass

    def smartsheet_job_sites_event(self, sheet_id, event):
        if event.objectType == "sheet":
            pass
        if event.objectType == "row":
            rowId = event.id
            print("Processing row event: ", rowId)
            row, columns = self.smartsheet.get_row(sheet_id, rowId)
            primary_column_id = next((key for key, value in columns.items() if value == 'Primary Column'), None)
            job_site = {}
            for cell in row.cells:
                if columns[cell.column_id] in self.smartsheet.JOB_SITES_SHEET_COLUMNS:
                    job_site[columns[cell.column_id]] = cell.value
            job_site = DataTransformer.smartsheet_to_wiw_job_site(job_site)
            print("Job site data transformed: ", job_site)
            job_id = self.wiw.create_or_update_job_site(job_site)['id']
            if job_site['id'] == '' or not job_site['id']:
                self.smartsheet.update_cell(sheet_id, rowId, primary_column_id, job_id)
            pass
        if event.objectType == "cell":
            pass

        # {'nonce': '4ab004fa-9a64-4296-9fe7-27e8cbdc0026', 'timestamp': '2025-02-16T10:20:26.079+00:00', 'webhookId': 8744272095668100, 'scope': 'sheet', 'scopeObjectId': 4990363940900740,
        # 'events': [{'objectType': 'sheet', 'eventType': 'updated', 'id': 4990363940900740, 'userId': 6308493297772420, 'timestamp': '2025-02-16T10:19:25.000+00:00'},
        # {'objectType': 'row', 'eventType': 'updated', 'id': 2095005077081988, 'userId': 6308493297772420, 'timestamp': '2025-02-16T10:19:25.000+00:00'},
        # {'objectType': 'cell', 'eventType': 'created', 'rowId': 2095005077081988, 'columnId': 8819538640719748, 'userId': 6308493297772420, 'timestamp': '2025-02-16T10:19:25.000+00:00'}]}

    def smartsheet_contacts_event(self, sheet_id, event: SmartsheetEvent):
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
