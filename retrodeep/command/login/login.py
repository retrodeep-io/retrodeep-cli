import requests
import webbrowser
from questionary import prompt
import json
import time
from pathlib import Path
import sys
import uuid
from yaspin import yaspin
from requests.exceptions import HTTPError, ConnectionError, Timeout, RequestException
# from PyInquirer import prompt

AUTH_BASE_URL = "https://auth.retrodeep.com"

class Style:
    GREY = '\033[90m'
    RED = '\033[31m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    CYAN = '\033[36m'
    UNDERLINE = '\033[4m'

def get_stored_credentials():
    credentials_file = Path.home() / '.retrodeep' / 'credentials.json'
    if credentials_file.exists():
        with open(credentials_file, 'r') as file:
            return json.load(file)
    else:
        return False
      
def initiate_github_oauth():
    session_id = str(uuid.uuid4())
    
    print(f"> {Style.UNDERLINE}{AUTH_BASE_URL}/login?session_id={session_id}{Style.RESET}")
    
    with yaspin(text=f"{Style.BOLD}Authenticating with GitHub...{Style.RESET}", color="cyan") as spinner:
        webbrowser.open(
            f"{AUTH_BASE_URL}/login?session_id={session_id}")

        time.sleep(3)

        wait_for_oauth_completion(session_id)

        polled_token = poll_for_token(session_id)
        spinner.text = f"{Style.BOLD}Authentication completed{Style.RESET}"
        spinner.ok("✔")
    return polled_token
    
def manage_user_session(username, access_token, email_address, retrodeep_access_token):
    app_dir = Path.home() / '.retrodeep'
    credentials_file = app_dir / 'credentials.json'

    # Check if the .retrodeep directory exists, create if not
    if not app_dir.exists():
        app_dir.mkdir()

    # Store credentials
    credentials = {
        'username': username,
        'access_token': access_token,
        'email_address': email_address,
        'retrodeep_access_token': retrodeep_access_token
    }
    with open(credentials_file, 'w') as file:
        json.dump(credentials, file)

def wait_for_oauth_completion(session_id, timeout=300, interval=3):
    start_time = time.time()

    while time.time() - start_time < timeout:
        # Check if the OAuth process is completed and the token is ready
        try:
            ready_response = requests.get(
                f"{AUTH_BASE_URL}/is_ready?session_id={session_id}")

            if ready_response.status_code == 200 and ready_response.json().get('ready'):
                # print("\n> Authentication completed.")
                break
            elif ready_response.status_code == 204:
                # OAuth process not completed, wait for the next check
                time.sleep(interval)
            else:
                # If any error occurs, raise an exception with the response
                raise Exception(
                    f"Error checking OAuth completion: {ready_response.text}")
        except HTTPError as http_err:
            print(f"{Style.RED}Error:{Style.RESET} HTTP error occurred: {http_err} - {ready_response.status_code}")
        except ConnectionError:
            print(f"{Style.RED}Error:{Style.RESET} Connection error: Please check your internet connection.")
        except Timeout:
            print(f"{Style.RED}Error:{Style.RESET} Timeout error: The request timed out. Please try again later.")
        except requests.exceptions.RequestException as err:
            print(f"Request error: {err}")

        time.sleep(1)  # Adjust for Dot update frequency
    if time.time() - start_time >= timeout:
        raise TimeoutError("Authentication timeout reached.")
    
def login_message(email):
    print(
        f"> You have successfully authenticated with GitHub as {Style.BOLD}{email}{Style.RESET}")
    print(
        f"Welcome aboard! Enjoy your journey with Retrodeep! 🚀")
    
def login_message2(email):
    print(
        f"> You have successfully authenticated with GitHub as {Style.BOLD}{email}{Style.RESET}")

def poll_for_token(session_id):
    while True:
        try:
            response = requests.get(
                f"{AUTH_BASE_URL}/get_token?state={session_id}")
            if response.status_code == 200:
                data = response.json()
                if 'access_token' in data and 'github_username' in data and 'email' in data and 'retrodeep_access_token' in data:
                    return {
                        "access_token": data.get('access_token'), 
                        "username": data.get('github_username'), 
                        "email_address": data.get('email'), 
                        "retrodeep_access_token": data.get('retrodeep_access_token')
                        }
                elif 'error' in data:
                    raise Exception(data['error'])
            elif response.status_code == 204:
                print("Authentication process not yet completed. Waiting...")
            else:
                print(
                    f"Server returned status code {response.status_code}. Response: {response.text}")
                raise Exception(
                    f"Server returned status code {response.status_code}. Response: {response.text}")

        except HTTPError as http_err:
            print(f"{Style.RED}Error:{Style.RESET} HTTP error occurred: {http_err} - {response.status_code}")
        except ConnectionError:
            print(f"{Style.RED}Error:{Style.RESET} Connection error: Please check your internet connection.")
        except Timeout:
            print(f"{Style.RED}Error:{Style.RESET} Timeout error: The request timed out. Please try again later.")
        except requests.exceptions.RequestException as err:
            print(f"{Style.RED}Error:{Style.RESET} Request error: {err}")
        except requests.RequestException as e:
            raise Exception(f"{Style.RED}Error:{Style.RESET} Request failed: {e}")
        time.sleep(5)

def login(args):
    credentials = get_stored_credentials()
    if credentials:
        print(
            f"> You are currently logged in to Retrodeep with the email address {Style.BOLD}{credentials['email_address']}{Style.RESET}")
        sys.exit(0)
    else:
        print("> No Credentials found. You are not currently logged in to retrodeep.")
        print("> Authenticate with GitHub to proceed with Retrodeep:")
        
            # Initiate GitHub OAuth process and retrieve token and email
        credentials = initiate_github_oauth()

        if credentials:
            token = credentials.get("access_token")
            username = credentials.get("username")
            email = credentials.get("email_address") 
            retrodeep_access_token = credentials.get("retrodeep_access_token")
            login_message(email)
            manage_user_session(username, token, email, retrodeep_access_token)
        else:
            print(f"{Style.RED}Error:{Style.RESET} {Style.BOLD}Authentication failed{Style.RESET}")

def login_for_workflow():
    credentials = get_stored_credentials()
    if credentials:
        return credentials
    else:
        print("> No Credentials found. You are not currently logged in to Retrodeep.")
        print("> Authenticate with GitHub to proceed with Retrodeep:")

             # Initiate GitHub OAuth process and retrieve token and email
        credentials = initiate_github_oauth()

        if credentials:
            token = credentials.get("access_token")
            username = credentials.get("username")
            email = credentials.get("email_address")
            retrodeep_access_token = credentials.get("retrodeep_access_token")
            login_message2(email)
            manage_user_session(username, token, email, retrodeep_access_token)
            return credentials
        else:
            print(f"{Style.RED}Error:{Style.RESET} {Style.BOLD}Authentication failed{Style.RESET}")
