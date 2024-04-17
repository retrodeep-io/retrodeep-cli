import requests
from datetime import datetime, timedelta
from tabulate import tabulate

from ..login.login import login_for_workflow

API_BASE_URL = "https://api.retrodeep.com/v1"

# ANSI escape codes for colors and styles
class Style:
    GREY = '\033[90m'
    RED = '\033[31m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    CYAN = '\033[36m'
    UNDERLINE = '\033[4m'

def list_projects(args):
    credentials = login_for_workflow()

    username = credentials['username']
    email = credentials['email_address']
    retrodeep_access_token = credentials['retrodeep_access_token']

    get_user_projects(username, retrodeep_access_token, email)

def get_user_projects(username, retrodeep_access_token, email_address):
    url = f"{API_BASE_URL}/projects"
    headers = {'Authorization': f'Bearer {retrodeep_access_token}'}
    data = {'username': username}
    response = requests.get(url, json=data, headers=headers)

    if response.status_code == 200:
        projects_data = response.json()

        if not projects_data:  # Check if the projects list is empty
            print(f"No projects found for {username}.")
            return

        projects_list = [
            {
                f'{Style.BOLD}Project Name{Style.RESET}': f" {Style.BOLD}{project['project_name']}{Style.RESET}",
                f'{Style.BOLD}Production URL{Style.RESET}': f"https://{project['domain_name']}",
                f'{Style.BOLD}Last Updated{Style.RESET}': format_days_since(project['updated_at'])
            }
            for project in projects_data
        ]
        print(f"> Projects for user {Style.BOLD}{username}{Style.RESET}\n")
        print(tabulate(projects_list, headers='keys', tablefmt='plain'))
    else:
        print(
            f"Failed to retrieve projects for {username}. Status Code: {response.status_code}")
        
def format_days_since(updated_at_str):
    updated_at = datetime.strptime(updated_at_str, '%a, %d %b %Y %H:%M:%S %Z')
    time_diff = datetime.utcnow() - updated_at
    days_diff = time_diff.days
    hours_diff = time_diff.seconds // 3600  # Convert seconds to hours

    if days_diff < 1:
        return f"{hours_diff}h"
    else:
        return f"{days_diff}d"