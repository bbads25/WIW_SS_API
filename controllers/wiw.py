import time
from re import search

import requests


class WhenIWork:
    def __init__(self):
        wiw_key = "f41e80d6473a0107cb193ce39b3a5cf5595fe475" #os.environ["wiw_key"]
        self.wiw_header = {"W-Key": f"{wiw_key}", "content-type": "application/json"}
        self.wiw_base_url = "https://api.wheniwork.com/2"
        self.wiw_login_url = "https://api.login.wheniwork.com/login"
        self.wiw_tag_url = "https://worktags.api.wheniwork-production.com"
        login_email = "m.haroon.s@pm.me"
        login_password = "Fast.410000"
        self.wiw_user_id = None
        logged_in = self.login(login_email, login_password)

    def login(self, email, password):
        r = requests.post(self.wiw_login_url, headers=self.wiw_header,
                          json={"email": email, "password": password})
        try:
            self.wiw_header["W-Token"] = r.json()['token']
            self.wiw_header["Authorization"] = r.json()['token']
            self.wiw_user_id = r.json()['person']['id']
            return True
        except Exception as e:
            print(f"login error: {e} - {r.content}")
            return False

    def get_users(self, search=None):
        url = self.wiw_base_url + '/users'
        params = {}
        if search:
            params['search'] = search

        r = requests.get(url, headers=self.wiw_header, params=params)
        return r.json()

    def get_user(self, user_id):
        url = self.wiw_base_url + '/users/' + str(user_id)
        r = requests.get(url, headers=self.wiw_header)
        if r.status_code == 200:
            return r.json()['user']
        else:
            return None

    def get_user_tags(self, user_id):
        tag_headers = self.wiw_header
        tag_headers['W-UserId'] = "50757204" # admin user id
        url = "https://worktags.api.wheniwork-production.com/users/" + str(user_id)
        r = requests.get(url, headers=tag_headers)
        tags = r.json()['data'].get('tags', [])
        tag_names = []
        for tag in tags:
            tag = self.get_tag(tag)
            tag_names.append(tag['name'])

        return tag_names


    def get_positions(self, search=None):
        url = self.wiw_base_url + '/positions'
        params = {}
        if search:
            params['search'] = search

        r = requests.get(url, headers=self.wiw_header, params=params)
        return r.json()['positions']

    def get_position(self, id):
        url = self.wiw_base_url + f'/positions/{id}'
        r = requests.get(url, headers=self.wiw_header)
        return r.json()['position']

    def get_locations(self, search=None):
        url = self.wiw_base_url + '/locations'
        params = {}
        if search:
            params['search'] = search
        r = requests.get(url, headers=self.wiw_header, params=params)
        return r.json()['locations']

    def get_location(self, id):
        url = self.wiw_base_url + f'/locations/{id}'
        r = requests.get(url, headers=self.wiw_header)
        return r.json()['location']

    def create_position(self, name):
        url = self.wiw_base_url + '/positions'
        r = requests.post(url, headers=self.wiw_header, json={"name": name})
        return r.json()['position']['id']

    def create_location(self, name):
        url = self.wiw_base_url + '/locations'
        r = requests.post(url, headers=self.wiw_header, json={"name": name})
        return r.json()['location']['id']

    def get_account(self, ):
        url = self.wiw_base_url + '/account'
        r = requests.get(url, headers=self.wiw_header)
        return r.json()['account']

    def get_tags(self, ):
        tag_headers = self.wiw_header
        tag_headers['W-UserId'] = "50757204"  # Heptic Fiverr's user_id
        url = "https://worktags.api.wheniwork-production.com/tags"
        r = requests.get(url, headers=tag_headers)
        return r.json()['data']

    def get_tag(self, id):
        tag_headers = self.wiw_header
        tag_headers['W-UserId'] = "50757204"  # Heptic Fiverr's user_id
        url = "https://worktags.api.wheniwork-production.com/tags/" + str(id)
        r = requests.get(url, headers=tag_headers)
        return r.json()['data']

    def create_tag(self, tag):
        tag_headers = self.wiw_header
        tag_headers['W-UserId'] = "50757204"
        url = "https://worktags.api.wheniwork-production.com/tags"
        r = requests.post(url, headers=tag_headers, json={"name": tag})
        return r.json()['data']['id']

    def compare_user_data(self, user, new_data):
        """
        Compare old_data and new_data to check if there are any differences.
        Normalize fields like None and empty strings and handle nested structures (lists, dictionaries).

        :param user: dict, old data
        :param new_data: dict, new data
        :return: bool, True if any value in new data differs from old data, False otherwise
        """
        user['tags'] = self.get_user_tags(user['id'])
        print("@@@@@@")
        print(user)
        print("--------")
        print(new_data)
        print("@@@@@@")

        def normalize_value(value):
            """Normalize a value for comparison."""
            if value is None or value == "":
                return ""  # Treat None and empty strings as equivalent
            if isinstance(value, list):
                return sorted(value)  # Sort lists for consistent comparison
            if isinstance(value, dict):
                return {k: normalize_value(v) for k, v in value.items()}  # Normalize dictionaries recursively
            if isinstance(value, int):
                return str(value)  # Convert integers to strings for comparison
            return value

        # Normalize and compare data
        for key, old_value in user.items():
            if key in new_data:
                new_value = normalize_value(new_data[key])
                if normalize_value(old_value) != new_value:
                    return True

        # Check if there are any extra keys in new_data not present in old_data
        for key in new_data:
            if key not in user:
                return True

        return False

    def create_or_update_user(self, data, user_id=None):
        print(f"Working on user: {data}")
        positions = self.get_positions()
        locations = self.get_locations()
        tags = self.get_tags()
        user_positions = []
        user_locations = []

        if "positions" in data:
            for position in data['positions']:
                position = position.strip()
                position_id = next((item['id'] for item in positions if item['name'] == position.strip()), None)
                if not position_id:
                    print(f"Position {position} not found, creating...")
                    position_id = self.create_position(position)
                    print(f"Position {position} created")
                user_positions.append(position_id)
        else:
            user_positions = []

        if "locations" in data:
            for location in data['locations']:
                location = location.strip()
                location_id = next((item['id'] for item in locations if item['name'] == location.strip()), None)
                if not location_id:
                    print(f"{location} not found in WiW, creating location...")
                    location_id = self.create_location(location)
                    print(f"Location {location} created")
                user_locations.append(location_id)
        else:
            user_locations = []

        data['positions'] = user_positions
        data['locations'] = user_locations

        if user_id:
            url = self.wiw_base_url + '/users/' + str(user_id)
            method = "PUT"
            user = self.get_user(user_id)
            if not self.compare_user_data(user, data):
                return {"status": "Change not required - wiw"}
        else:
            url = self.wiw_base_url + '/users'
            method = "POST"

        r = requests.request(method, url, headers=self.wiw_header, json=data)
        if r.status_code == 200:
            user = r.json()['user']
            if "tags" in data:
                # update tags
                tag_ids = []
                tag_created = False
                for tag in data['tags']:
                    tag = tag.strip()
                    tag_id = next((item['id'] for item in tags if item['name'] == tag), None)
                    if not tag_id:
                        print(f"Tag {tag} not found, creating...")
                        tag_id = self.create_tag(tag)
                        print(f"Tag {tag} created: {tag_id}")
                        tag_created = True

                    tag_ids.append(tag_id)

                if tag_created:
                    print("All required tags created successfully")
                    time.sleep(20)

                tag_headers = self.wiw_header
                tag_headers['W-UserId'] = "50757204"  # Heptic Fiverr's user_id
                url = f"https://worktags.api.wheniwork-production.com/users/{user['id']}"
                r = requests.put(url, headers=tag_headers, json={"tags": tag_ids})
                print(f"Tags updated: {r.json()}")
            return user
        else:
            print("Cannot create or update user: {}".format(r.content))
            print(r.status_code)
            return False

    def create_or_update_job_site(self, data):
        url = self.wiw_base_url + '/sites'
        if 'id' in data and data['id'] and data['id'] != '':
            # site exists
            url = url + '/' + str(data['id'])
            method = "PUT"
            payload = {
                "name": data['name'],
                "address": data['address'],
            }
            r = requests.request(method, url, headers=self.wiw_header, json=payload)
            return data
        else:
            # site id not in smartsheet
            sites = requests.get(url, headers=self.wiw_header)
            print(sites.json(), sites.status_code)
            similar = False
            if sites.status_code == 200:
                # Look if site with same name present
                for site in sites.json()['sites']:
                    if site['name'] == data['name']:
                        data['id'] = site['id']
                        if data['id'] == site['id'] and data['name'] == data['name'] and data['address'] == data['address']:
                            similar = True

            # if site not found, then create in wiw else update it
            if data['id'] == '' or not data['id']:
                method = "POST"
                payload = {
                    "name": data['name'],
                    "address": data['address'],
                }
                r = requests.request(method, url, headers=self.wiw_header, json=payload)
                return r.json()['site']
            else:
                if not similar:
                    return self.create_or_update_job_site(data)
                else:
                    return data

    def get_sites(self, search=None):
        url = self.wiw_base_url + '/sites'
        r = requests.get(url, headers=self.wiw_header)
        if r.status_code == 200:
            sites = r.json()['sites']
            return sites if not search else next((site for site in sites if site['name'] == search), False)

        else:
            return False

    def create_or_update_shift(self, data):
        url = self.wiw_base_url + '/shifts'
        if 'id' in data and data['id'] and data['id'] != '':
            # shift exists
            url = url + '/' + str(data['id'])
            method = "PUT"
            r = requests.request(method, url, headers=self.wiw_header, json=data)
            print("Shift updated: ", r.json())
        else:
            method = "POST"
            print(url)
            print(self.wiw_header)
            r = requests.request(method, url, headers=self.wiw_header, json=data)
            print("Shift created: ", r.json())

        if r.status_code == 200:
            shift = r.json()['shift']
            return shift
        else:
            return False

    def publish_shifts(self, shift_ids):
        url = self.wiw_base_url + '/shifts/publish'
        method = "POST"
        payload = {"ids": shift_ids}
        r = requests.request(method, url, headers=self.wiw_header, json=payload)
        if r.status_code == 200:
            return True

if __name__ == '__main__':
    o = WhenIWork()
    print(o.get_user_tags(51145001))