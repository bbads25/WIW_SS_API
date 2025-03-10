from controllers.wiw import WhenIWork


class DataTransformer:
    wiw_contact_columns = ['firstName', 'lastName', 'email', 'phoneNumber', 'locationId', 'positionId', 'role']
    smartsheet_contact_columns = ['First Name', 'Last Name', 'WIW_Position', 'WIW_Schedule', 'Capabilities', 'Email',
                                  'Phone Number']

    wiw_job_site_columns = ["name", "address"]
    smartsheet_job_site_columns = ["Operating Site", "Address"]

    def __init__(self):
        pass

    @staticmethod
    def smartsheet_to_wiw_shift(shift, operator = "0"):
        notes = [
            f"Game ID: {shift['Game ID']}",
            f"Date: {shift['Date']}",
            f"Client Team: {shift["Client Team"]}",
            f"Match: {shift["Home Team"]} @ {shift['Away Team']}",
            f"TV Network: {shift['TV Network']}"
        ]
        end_time = shift['Date'] +  ' ' + shift['Start Time (EST)'] if 'Start Time (EST)' in shift and shift['Start Time (EST)'] else shift['Date']
        shift['Call Time (Local)'] = shift['Call Time (Local)'].replace('ET', '').strip() if 'Call Time (Local)' in shift and shift['Call Time (Local)'] else None
        payload = {
            "user_id": operator,
            "location_id": shift['location_id'] if 'location_id' in shift else '',
            'position_id': shift['position_id'] if 'position_id' in shift else '',
            "site_id": shift['site_id'] if 'site_id' in shift else '',
            "start_time": shift['Date'] +  ' ' + shift['Call Time (Local)'] if shift['Call Time (Local)'] else shift['Date'],
            "end_time": end_time,
            "notes": " | ".join(notes),
            # "tags": shift['tags'] if 'tags' in shift else '',
            # handle shift task list using https://apidocs.wheniwork.com/external/index.html?repo=tasks&branch=main#tag/Task-Lists/paths/~1task-lists/post
        }

        return payload

    @staticmethod
    def smartsheet_to_wiw_job_site(job_site):
        payload = {
            "id": job_site['Primary Column'] if 'Primary Column' in job_site else '',
            "name": job_site["Operating Site"] if 'Operating Site' in job_site else "",
            "address": job_site["Address"] if 'Address' in job_site else ""
        }

        return payload

    @staticmethod
    def wiw_to_smartsheet_contact(contact, tags, wiw: WhenIWork):
        column_mapping = {
            'id': 'Primary Column',
            'userId' :'Primary Column',
            'firstName': 'First Name',
            'lastName': 'Last Name',
            'positionId': 'WIW_Position',
            'locationId': 'WIW_Schedule',
            # 'role': None,
            # 'tags': 'Capabilities',
            'email': 'Email',
            'phoneNumber': 'Phone Number',
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'phone_number': 'Phone Number',
        }
        positions = ""
        if 'positions' in contact:
            for position in contact['positions']:
                p = wiw.get_position(position)
                p = p['name']
                if positions:
                    positions = positions + "\n" + p
                else:
                    positions = p

        locations = ""

        if 'locations' in contact:
            for location in contact['locations']:
                location = wiw.get_location(location)
                location = location['name']
                if locations:
                    locations = locations + "\n" + location
                else:
                    locations = location

        # Initialize the transformed contact with Smartsheet keys and default empty values
        transformed_contact = {col: None for col in DataTransformer.smartsheet_contact_columns}

        # Map WIW data to Smartsheet format
        for wiw_key, smartsheet_key in column_mapping.items():
            if wiw_key in contact:
                transformed_contact[smartsheet_key] = contact[wiw_key]

        if positions != "":
            transformed_contact['WIW_Position'] = positions
        if locations != "":
            transformed_contact['WIW_Schedule'] = locations

        if tags:
            transformed_contact['Capabilities'] = '\n'.join(tags)

        # Remove keys with None values
        transformed_contact = {key: str(value) for key, value in transformed_contact.items() if value is not None}

        return transformed_contact

    @staticmethod
    def smartsheet_to_wiw_contact(contact):
        for key, value in contact.items():
            if key in {"Capabilities", "WIW_Position", "WIW_Schedule"}:
                value = value.split(', ')
                contact.update({key: value})

        payload = {
            "id": contact['Primary Column'] if 'Primary Column' in contact else '',
            "email": contact['Email'] if 'Email' in contact else '',
            "first_name": contact['First Name'] if 'First Name' in contact else '',
            "last_name": contact['Last Name'] if 'Last Name' in contact else '',
            "phone_number": contact['Phone Number'] if 'Phone Number' in contact else "",
            "positions": contact['WIW_Position'] if 'WIW_Position' in contact else [],
            "locations": contact['WIW_Schedule'] if 'WIW_Schedule' in contact else [],
            "tags": contact['Capabilities'] if 'Capabilities' in contact else [],
        }


        return payload