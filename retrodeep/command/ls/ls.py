import requests
from datetime import datetime, timedelta
from ..login.login import login_for_workflow
from tabulate import tabulate

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

def list_projects_deployments(args):
    credentials = login_for_workflow()

    username = credentials['username']
    email = credentials['email_address']
    retrodeep_access_token = credentials['retrodeep_access_token']

    get_project_deployments(username, retrodeep_access_token, email, args.deployment_url)
        
def get_project_deployments(username, retrodeep_access_token, email_address, project_name):
    url = f"{API_BASE_URL}/deployments"
    headers = {'Authorization': f'Bearer {retrodeep_access_token}'}
    data = {'username': username, 'project_name':project_name}
    response = requests.get(url, json=data, headers=headers)

    if response.status_code == 200:
        deployments_data = response.json()

        if not deployments_data:  # Check if the projects list is empty
            print(f"No deployments found for {username}.")
            return

        deployment_list = [
            {
                f'{Style.BOLD}Deployment ID{Style.RESET}': f"{Style.BOLD}{deployment['deployment_id']}{Style.RESET}",
                f'{Style.BOLD}Deployment{Style.RESET}': f"https://{deployment['url']}",
                f'{Style.BOLD}Status{Style.RESET}': f"{Style.BOLD}{deployment['status']}{Style.RESET}",
                f'{Style.BOLD}Created{Style.RESET}': format_days_since(deployment['created_at'])
            }
            for deployment in deployments_data
        ]
        print(f"> Deployments of project {Style.BOLD}{project_name}{Style.RESET} for user {Style.BOLD}{username}{Style.RESET}\n")
        print(tabulate(deployment_list, headers='keys', tablefmt='plain'))
    else:
        print(
            f"Failed to retrieve Deployments for {project_name}. Status Code: {response.status_code}")

def format_days_since(updated_at_str):
    updated_at = datetime.strptime(updated_at_str, '%a, %d %b %Y %H:%M:%S %Z')
    time_diff = datetime.utcnow() - updated_at
    days_diff = time_diff.days
    hours_diff = time_diff.seconds // 3600  # Convert seconds to hours

    if days_diff < 1:
        return f"{hours_diff}h"
    else:
        return f"{days_diff}d"