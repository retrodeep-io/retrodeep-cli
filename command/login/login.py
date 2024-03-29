import requests
from flask import Flask, request
import webbrowser
from github import Github
# from PyInquirer import prompt
from questionary import prompt
import git
import json
import base64
from nacl import encoding, public
import time
from tqdm import tqdm
from datetime import datetime, timedelta
from pathlib import Path
from clint.textui import progress
import sys
import uuid
from tabulate import tabulate
from yaspin import yaspin
from alive_progress import alive_bar

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

    webbrowser.open(
        f"{AUTH_BASE_URL}/login?session_id={session_id}")

    time.sleep(3)

    wait_for_oauth_completion(session_id)

    return poll_for_token(session_id)
    
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
        time.sleep(1)  # Adjust for Dot update frequency
    if time.time() - start_time >= timeout:
        raise TimeoutError("Authentication timeout reached.")
    
def login_message(email):
    print(
        f"> You have successfully authenticated with GitHub as {Style.BOLD}{email}{Style.RESET}")
    print(
        f"Welcome aboard! Enjoy your journey with Retrodeep! 🚀")

def poll_for_token(session_id):
    while True:
        try:
            response = requests.get(
                f"{AUTH_BASE_URL}/get_token?state={session_id}")
            if response.status_code == 200:
                data = response.json()
                if 'access_token' in data and 'github_username' in data and 'email' in data and 'retrodeep_access_token' in data:
                    return data['access_token'], data['github_username'], data['email'], data['retrodeep_access_token']
                elif 'error' in data:
                    raise Exception(data['error'])
            elif response.status_code == 204:
                print("Authentication process not yet completed. Waiting...")
            else:
                print(
                    f"Server returned status code {response.status_code}. Response: {response.text}")
                raise Exception(
                    f"Server returned status code {response.status_code}. Response: {response.text}")
        except requests.RequestException as e:
            raise Exception(f"Request failed: {e}")
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
        
        with yaspin(text=f"{Style.BOLD}Authenticating...{Style.RESET}", color="cyan") as spinner:
             # Initiate GitHub OAuth process and retrieve token and email
            token, username, email, retrodeep_access_token = initiate_github_oauth()
            if token:
                spinner.text = f"{Style.BOLD}Authentication completed{Style.RESET}"
                spinner.ok("✔")
        # print("Authentication completed.")
        if username and email and token and retrodeep_access_token:
            login_message(email)
            manage_user_session(username, token, email, retrodeep_access_token)
        else:
            print("> Failed to authenticate.")
            sys.exit(1)

def login_for_workflow():
    credentials = get_stored_credentials()
    if credentials:
        return credentials
    else:
        print("> No Credentials found. You are not currently logged in to Retrodeep.")
        print("> Authenticate with GitHub to proceed with Retrodeep:")

        with yaspin(text=f"{Style.BOLD}Authenticating...{Style.RESET}", color="cyan") as spinner:
             # Initiate GitHub OAuth process and retrieve token and email
            token, username, email, retrodeep_access_token = initiate_github_oauth()
            if token:
                spinner.ok("✔")

        # If the user was successfully added or already exists, store their session
        if username and email and token and retrodeep_access_token:
            login_message(email)
            manage_user_session(username, token, email, retrodeep_access_token)
            credentials = get_stored_credentials()
            return credentials
        else:
            print("> Failed to authenticate")
            sys.exit(1)