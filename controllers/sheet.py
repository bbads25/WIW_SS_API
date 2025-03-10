import smartsheet

class Smartsheet:
    CONTACTS_SHEET_ID = 5103766730657668
    JOB_SITES_SHEET_ID = 4990363940900740
    EVENTS_SHEET_ID = 3021164519575428
    MASTER_LOOKUP_ID = 7822439689965444

    CONTACT_SHEET_COLUMNS = ['First Name', 'Last Name', 'WIW_Position', 'WIW_Schedule', 'Capabilities', 'Email',
                             'Phone Number', "Name", "Primary Column"]
    JOB_SITES_SHEET_COLUMNS = ["Operating Site", "Address", "Primary Column"]
    EVENTS_SHEET_COLUMNS = ["Operator", "Operating Site", "Date", "Game ID", "Client Team",
                            "Home Team", "Away Team", "TV Network", "Call Time (Local)", "Start Time (EST)"]
    MASTER_LOOKUP_COLUMNS = ["1. Team", "WIW_Schedule", "WIW_Position", "Capability_Required", "WIW_Shift_Task_Lists"]

    def __init__(self):
        SMARTSHEET_KEY = "5WJCTGhYBqjXx7UeppXrIaSSWASmcp3VqNr6T"
        self.client = smartsheet.Smartsheet(SMARTSHEET_KEY)

    def initialize_webhook(self, webhook_url):
        if not self.check_webhook(webhook_url, self.CONTACTS_SHEET_ID):
            self.add_webhook("Contacts-Python", webhook_url, self.CONTACTS_SHEET_ID)

        if not self.check_webhook(webhook_url, self.JOB_SITES_SHEET_ID):
            self.add_webhook("JobSites-Python", webhook_url, self.JOB_SITES_SHEET_ID)

        if not self.check_webhook(webhook_url, self.EVENTS_SHEET_ID):
            self.add_webhook("Events-Python", webhook_url, self.EVENTS_SHEET_ID)


    def check_webhook(self, webhook_url, sheet_id):
        response = self.client.Webhooks.list_webhooks(
            page_size=100,
            page=1,
            include_all=True
        )
        data = response.data
        for webhook in data:
            if webhook.callback_url == webhook_url and webhook.scope_object_id == sheet_id:
                if webhook.status == "ENABLED":
                    return True
                else:
                    w = self.enable_webhook(webhook.id)
                    if w.status == "ENABLED":
                        return True
        return False

    def get_column_name(self, sheet_id, column_id):
        column = self.client.Sheets.get_column(
            sheet_id,  # sheet_id
            column_id,  # column_id
            )

        return column.title

    def add_webhook(self, name, url, sheet_id):
        print("Adding smartsheet webhook: ", name)
        new_webhook = self.client.models.Webhook({
            "name": name,
            "callbackUrl": url,
            "scope": "sheet",
            "scopeObjectId": sheet_id,  # 2879486383050628 EVENT,
            "events": ["*.*"],
            "version": 1
        })

        created_webhook = self.client.Webhooks.create_webhook(new_webhook)
        print("Webhook ID: ", created_webhook.data.id)
        WEBHOOK_ID = created_webhook.data.id
        enabled_webhook = self.enable_webhook(WEBHOOK_ID)
        if enabled_webhook.status == "ENABLED":
            print("Webhook successfully added!")
            return enabled_webhook
        else:
            print("Error creating webhook: " + str(enabled_webhook))
            return False

    def enable_webhook(self, webhook_id):
        self.client.Webhooks.update_webhook(
            webhook_id,  # webhook_id
            self.client.models.Webhook({
                'enabled': True}))

        webhook = self.client.Webhooks.get_webhook(webhook_id)
        return webhook

    def get_sheets(self, include_all=False):
        sheets = {}
        response = self.client.Sheets.list_sheets(
            include_all=include_all)  # Call the list_sheets() function and store the response object

        for sheet in response.data:
            sheets[sheet.id] = sheet.name

        return sheets

    def get_sheet(self, sheet_id):
        sheet = self.client.Sheets.get_sheet(sheet_id, exclude=["nonexistentCells"])
        sheet_columns = {}
        for col in sheet.columns:
            sheet_columns[col.id] = col.title
        return sheet, sheet_columns

    def get_row(self, sheet_id, row_id):
        row_data = self.client.Sheets.get_row(
            sheet_id,  # sheet_id
            row_id,  # row_id
            exclude=['linkInFromCellDetails', 'linksOutToCellsDetails', 'nonexistentCells'],
            include=['columns']
        )
        sheet_columns = {}
        for col in row_data.columns:
            sheet_columns[col.id] = col.title

        return row_data, sheet_columns

    def get_cell_history(self, sheet_id, row_id, column_id):
        cell_history = self.client.Cells.get_cell_history(
            sheet_id,  # sheet_id
            row_id, column_id,
            page_size=1,
            page=1
        )

        return cell_history.data

    def get_column_data(self, sheet_id, column_id):
        sheet, columns = self.get_sheet(sheet_id)
        column_data = []

        for row in sheet.rows:
            # Find the cell in the current row that matches the column_id
            cell = next((cell for cell in row.cells if cell.column_id == column_id), None)
            if cell:
                # Append the rowId and the cell value to the result list
                column_data.append({row.id: cell.value})

        return column_data

    def update_cell(self, sheet_id, row_id, column_id, value):
        # Build new cell value
        new_cell = self.client.models.Cell()
        new_cell.column_id = column_id
        new_cell.value = str(value)
        # new_cell.strict = False

        # Build the row to update
        new_row = self.client.models.Row()
        new_row.id = row_id
        new_row.cells.append(new_cell)

        # Update rows
        updated_row = self.client.Sheets.update_rows(
            sheet_id,  # sheet_id
            [new_row])

        return updated_row  # .data will show list of row objects as passed

    def update_row(self, sheet_id, row_id, data):
        # data is [{col1: value, col2: value}]
        # Build the row to update
        new_row = self.client.models.Row()
        new_row.id = row_id

        for cell in data:
            for key, value in cell.items():
                # Build new cell value
                new_cell = self.client.models.Cell()
                new_cell.column_id = key
                new_cell.value = str(value)
                # new_cell.strict = False
                new_row.cells.append(new_cell)

        # Update rows
        updated_row = self.client.Sheets.update_rows(
            sheet_id,  # sheet_id
            [new_row])

        return updated_row  # .data will show list of row objects as passed

    def create_row(self, sheet_id, data):
        row = smartsheet.models.Row()
        row.to_bottom = True
        for cell in data:
            for key, value in cell.items():
                new_cell = self.client.models.Cell()
                new_cell.column_id = key
                new_cell.value = str(value)
                row.cells.append(new_cell)

        response = self.client.Sheets.add_rows(
            sheet_id,  # sheet_id
            [row])

        return response

    def filter_sheet(self, sheet_data, sheet_columns, req_columns):
        filtered_sheet = []
        for row in sheet_data.rows:
            data = {"rowId": row.id}
            for cell in row.cells:
                if sheet_columns[cell.column_id] in req_columns:
                    data[sheet_columns[cell.column_id]] = cell.value
            filtered_sheet.append(data)

        return filtered_sheet

    def check_row_existence(self, data, primary_column, first_name, last_name):
        # Check for Primary Column match
        for row in data:
            if row.get('Primary Column') == primary_column:
                return row

        # Check for First Name and Last Name match
        for row in data:
            if row.get('First Name') == first_name and row.get('Last Name') == last_name:
                return row

        # If no match is found
        return False

    def compare_rows(self, old_data, new_data):
        """
        Compare two dictionaries (data1 as old data, data2 as new data) to check if there are differences.
        Normalize fields like 'Capabilities', 'WIW_Position', and 'WIW_Schedule' before comparison.

        :return: bool, True if any value in new data differs from old data, False otherwise
        """
        # Fields to normalize
        if not old_data or not new_data:
            return True

        fields_to_normalize = {"Capabilities", "WIW_Position", "WIW_Schedule"}

        # Normalize new data
        normalized_new_data = {}
        for key, value in new_data.items():
            if key in fields_to_normalize and isinstance(value, str):
                # Replace '\n' with ', ' and sort items
                normalized_new_data[key] = ", ".join(sorted(value.replace("\n", ", ").split(", ")))
            elif value is None:
                normalized_new_data[key] = ""
            else:
                normalized_new_data[key] = value

        normalized_old_data = {}
        for key, value in old_data.items():
            if key in fields_to_normalize and isinstance(value, str):
                # Sort items for comparison
                normalized_old_data[key] = ", ".join(sorted(value.split(", ")))
            elif value is None:
                normalized_old_data[key] = ""
            else:
                normalized_old_data[key] = value

        # Compare data1 and normalized data2
        for key, value in normalized_old_data.items():
            if key in normalized_new_data and normalized_new_data[key] != value:
                return True

        return False

    def create_or_update_row(self, sheet_id, row_data):
        # {'First Name': 'sss', 'Last Name': '2222', 'WIW_Position': 'Watcher\nOperator2', 'WIW_Schedule': 'NYC_Op_Schedule', 'Capabilities': 'Baseball\nBaseball_Chroma\nHockey', 'Email': 'hs@hs.com', 'Phone Number': '', 'Primary Column': '51145000'}
        sheet, columns = self.get_sheet(sheet_id)
        sheet = self.filter_sheet(sheet, columns, list(row_data.keys()))
        row = self.check_row_existence(sheet, row_data['Primary Column'], row_data['First Name'], row_data['Last Name'])
        print("######### AVOID CIRCULER CALLS")
        print(row)
        print("@@@@@@@")
        print(row_data)
        print("--------")
        print("Change Required: ", self.compare_rows(row, row_data))
        print("#########")

        if not self.compare_rows(row, row_data):
            return {"status": "Change not required - smartsheet"}

        reversed_cols = {value: key for key, value in columns.items()}
        row_data['Name'] = row_data['First Name'] + " " + row_data['Last Name']
        update_data = []
        for key, value in row_data.items():
            if not key in ['First Name', 'Last Name']:
                key = reversed_cols[key]  # get column_id
                update_data.append({key: value})

        print("Data to update: ", update_data)
        if row:
            row_id = row['rowId']
            response = self.update_row(sheet_id, row_id, update_data)
        else:
            # Row not found, create row
            # row data should be [{colId: value}]
            response = self.create_row(sheet_id, update_data)

        return response

    def master_lookup(self, client_team):
        sheet, columns = self.get_sheet(self.MASTER_LOOKUP_ID)
        sheet = self.filter_sheet(sheet, columns, self.MASTER_LOOKUP_COLUMNS)
        for row in sheet:
            print("Master lookup: ", row)
            print(row['1. Team'])
            break
        result = next((row for row in sheet if '1. Team' in row and row['1. Team'] == client_team), None)
        return result

if __name__ == '__main__':
    o = Smartsheet()
    sheet, columns = o.get_sheet(o.CONTACTS_SHEET_ID)
    print(columns)
    for row in sheet.rows:
        print(row)
        break
    row_id = row.id
    column_id = 8139451679330180  # WIW_Position # 8280189167685508 # primary column
    value = "Operator"
    cell_history = o.get_cell_history(o.CONTACTS_SHEET_ID, row_id, column_id)
    print(cell_history[0])
    for cell in cell_history:
        print(cell)
    # p = o.update_cell(o.CONTACTS_SHEET_ID, row_id, column_id, value)
    # p = o.update_row(o.CONTACTS_SHEET_ID, row_id, [{
    #     column_id: value
    # }])
