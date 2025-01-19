from controllers.sheet import Smartsheet
from controllers.wiw import WhenIWork
from transformers.data_transformer import DataTransformer

sheet = Smartsheet()
wiw = WhenIWork()
sheet_cols = ['First Name', 'Last Name', 'WIW_Position', 'WIW_Schedule', 'Capabilities', 'Email', 'Phone Number']
sheet_id = sheet.CONTACTS_SHEET_ID


def initial_load():
    data, columns = sheet.get_sheet(sheet_id)
    columns = {}
    primary_column_id = None
    for col in data.columns:
        columns[col.id] = col.title
        if col.title == "Primary Column":
            primary_column_id = col.id

    for row in data.rows:
        contact = {}
        for cell in row.cells:
            if columns[cell.column_id] in sheet_cols:
                contact[columns[cell.column_id]] = cell.value

        contact = DataTransformer.smartsheet_to_wiw_contact(contact)
        print(contact)
        user = create_or_update_user(contact)
        # Add ID to smartsheet
        if user:
            print(user)
            row_id = row.id
            value = user['id']
            try:
                print(sheet.update_cell(sheet.CONTACTS_SHEET_ID, row_id, primary_column_id, value))
            except Exception as e:
                print(f"Error updating row {e}")


def create_or_update_user(contact):
    name = f"{contact['first_name']} {contact['last_name']}"
    user = wiw.get_users(name)
    if user and len(user['users']) > 0:
        # user exists in wiw so update it
        print(f"User {name} {user['users'][0]['id']} already exists, updating...")
        r = wiw.create_or_update_user(contact, user_id=user['users'][0]['id'])
    else:
        print(f"User {name} does not exist, creating...")
        r = wiw.create_or_update_user(contact)

    if not r:
        print(f'Error processing user {name}')
        return None
    else:
        print(f"User {name} processed!\n")
        print(r)
        return r

if __name__ == '__main__':
    initial_load()