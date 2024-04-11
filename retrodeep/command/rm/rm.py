import requests
from questionary import prompt
from datetime import datetime, timedelta
from pathlib import Path
from clint.textui import progress
import sys

from ..login.login import login_for_workflow

from ..deploy.deploy import check_project_exists
from ..deploy.deploy import confirm_action

from cryptography.fernet import Fernet

# framework = None

# ANSI escape codes for colors and styles
class Style:
    GREY = '\033[90m'
    RED = '\033[31m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    CYAN = '\033[36m'
    UNDERLINE = '\033[4m'

API_BASE_URL = "https://api.retrodeep.com/v1"

def delete_project(args):
    credentials = login_for_workflow()

    username = credentials['username']
    retrodeep_access_token = credentials['retrodeep_access_token']

    project_name = args.project_name
    if project_name is None:
        print(f"{Style.RED}Error:{Style.RESET} '{Style.BOLD}retrodeep rm{Style.RESET}' is missing required argument 'project name'")
        print(
          f"""
 Usage: {Style.BOLD}retrodeep rm{Style.RESET} [project name | project ID]

 Remove a project deployment via ID or name..

 Options:
 -h, --help            Displays usage information.        

 Examples:

 - Remove a project deployment with name 'test-app'

   $ retrodeep rm test-app

 - Remove a project deployment with deploymentID 

   $ retrodeep rm deploymentID

	    """)
        sys.exit(1)
    else:
        if check_project_exists(username, project_name, retrodeep_access_token):
            print(
                f"You're about to remove the project: {Style.BOLD}{project_name}{Style.RESET}")
            print("This would permanently delete all its deployments and dependencies")

            if confirm_action(f"> {Style.RED}{Style.BOLD}Are you sure?{Style.RESET}"):
                delete_project_request(
                    username, args.project_name, retrodeep_access_token)
            else:
                print("> Operation canceled")
                sys.exit(1)
        else:
            print(
                f'> There are no deployments or projects matching {Style.BOLD}{project_name}{Style.RESET}.')

def delete_project_request(username, project_name, retrodeep_access_token):
    url = f"{API_BASE_URL}/projects/{project_name}"
    headers = {'Authorization': f'Bearer {retrodeep_access_token}'}
    data = {'username': username}

    response = requests.delete(url, json=data, headers=headers)

    if response.status_code == 200:
        print(f"Bravo! Deleted 1 project {Style.BOLD}{project_name}{Style.RESET}")
    else:
        print(
            f"Failed to delete project. Status Code: {response.status_code}")
        print(response.json())