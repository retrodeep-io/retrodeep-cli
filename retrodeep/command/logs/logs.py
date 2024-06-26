import requests
from datetime import datetime, timedelta
import re
from requests.exceptions import HTTPError, ConnectionError, Timeout, RequestException


from ..login.login import login_for_workflow

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
SSE_BASE_URL = "https://sse.retrodeep.com/stream"
AUTH_BASE_URL = "https://auth.retrodeep.com"

def fetch_and_display_logs(args):
    credentials = login_for_workflow()
    retrodeep_access_token = credentials['retrodeep_access_token']

    deployment_url = args.deployment_url

    if deployment_url is None:
        print(f"{Style.RED}Error:{Style.RESET}: Deployment URL is required.")
        print(
          f"""
 Usage: {Style.BOLD}retrodeep logs{Style.RESET} [deployment URL | deployment ID]

 Display logs for a Retrodeep deployment.

 Options:
 -h, --help            Displays usage information.        

 Examples:

 - Show logs for a deployment using deployment url

   $ retrodeep logs example_deployment_url

	    """)
    
    else:
        subdomain = remove_https(deployment_url)

        url = f"{API_BASE_URL}/deployments/{subdomain}/logs"
        headers = {'Authorization': f'Bearer {retrodeep_access_token}'}

        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                logs = response.json()
                print(f"> Fetched logs for deployment {Style.BOLD}{logs.get('deployment_url')}{Style.RESET}")
                for log in logs.get('logs'):
                    print(f"{Style.GREY}{log['timestamp']}{Style.RESET}  {log['message']}")
            elif response.status_code == 404:
                print(f"> A deployment with the url {Style.BOLD}{subdomain}{Style.RESET} does not exist.")
        except HTTPError as http_err:
            print(f"{Style.RED}Error:{Style.RESET} HTTP error occurred: {http_err} - {response.status_code}")
        except ConnectionError:
            print(f"{Style.RED}Error:{Style.RESET} Connection error: Please check your internet connection.")
        except Timeout:
            print(f"{Style.RED}Error:{Style.RESET} Timeout error: The request timed out. Please try again later.")
        except requests.exceptions.RequestException as err:
            print(f"{Style.RED}Error:{Style.RESET} Request error: {err}")

def remove_https(url):
    # Regular expression to match and remove 'https://' if it exists
    pattern = r'^https?://(.+)$'

    # Search for the pattern in the given URL and remove 'https://' or 'http://' if present
    match = re.match(pattern, url)

    if match:
        # Return the URL without 'https://'
        return match.group(1)
    else:
        # Return the original URL if 'https://' is not present
        return url