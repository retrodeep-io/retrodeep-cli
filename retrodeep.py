import requests
from flask import Flask, request
import webbrowser
import threading
from github import Github
# from PyInquirer import prompt
from questionary import prompt
import git
import json
import base64
from nacl import encoding, public
import argparse
import os
import shutil
import time
from tqdm import tqdm
from datetime import datetime, timedelta
from pathlib import Path
from clint.textui import progress
import random
import string
import itertools
import subprocess
import re
import signal
import sys, traceback
import waitress
import secrets
import uuid
from tabulate import tabulate
from yaspin import yaspin
import glob
import http.server
import socketserver
import randomname

from cryptography.fernet import Fernet

app = Flask(__name__)

# framework = None

API_BASE_URL = "https://api.retrodeep.com/v1"
SCM_BASE_URL = "https://scm.retrodeep.com"
DEPLOY_BASE_URL = "https://deploy.retrodeep.com/v1"
AUTH_BASE_URL = "https://auth.retrodeep.com"
__version__ = "1.0.0"

# ANSI escape codes for colors and styles
class Style:
    GREY = '\033[90m'
    RED = '\033[31m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    CYAN = '\033[36m'
    UNDERLINE = '\033[4m'

class CustomFormatter(argparse.HelpFormatter):
    def _format_usage(self, usage, actions, groups, prefix):
        if prefix is None:
            prefix = 'usage: '
        # Return your custom usage string
        return f"{prefix}retrodeep [options] [command]\n\n"
    
    def _format_action(self, action):
        parts = super()._format_action(action).split('\n')
        parts_filtered = [part for part in parts if not part.strip().startswith('{')]
        return '\n'.join(parts_filtered)

# Set to store previously generated codes to ensure uniqueness
generated_codes = set()

class QuietHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

class MyTCPServer(socketserver.TCPServer):
    allow_reuse_address = True 

def signal_handler(signal_received, frame):
    sys.exit(0)


# Determine the configuration directory
home = os.path.expanduser("~")
config_directory = os.path.join(home, ".retrodeep")
if not os.path.exists(config_directory):
    os.makedirs(config_directory)

def deploy_from_local(username, email, retrodeep_access_token):

    project_name = name_of_project_prompt(username, retrodeep_access_token)

    while True:
        directory_question = {
            'type': 'input',
            'name': 'directory',
            'message': 'Enter the path to the directory containing your codebase:',
            'default': './'
        }
        directory = prompt(directory_question)['directory']

        # Convert the directory to an absolute path
        absolute_path = os.path.abspath(directory)

        if directory and os.path.exists(absolute_path) and os.path.isdir(absolute_path):
            # Check for the existence of .html file
            if glob.glob(os.path.join(absolute_path, '*.html')) or glob.glob(os.path.join(absolute_path, 'package.json')) :
                print(
                    f"> You are about to deploy from the directory: {Style.BOLD}{absolute_path}{Style.RESET}")
                break
            else:
                print("> There is no .html or package.json file in the provided path.")
                choice_question = {
                    'type': 'list',
                    'name': 'choice',
                    'message': 'What would you like to do?',
                    'choices': ['Provide a different directory', 'Exit']
                }
                choice = prompt(choice_question)['choice']
                if choice == 'Exit':
                    print("Exiting the application.")
                    return
        else:
            print("> Invalid directory. Please enter a valid directory path.")

    framework = check_files_and_framework(absolute_path)
    
    if framework != "html":
        print(f"> Auto-detected Project Settings for {Style.BOLD}{framework}{Style.RESET}:")
        # print(f"What's your {Style.BOLD}Build command{Style.RESET}:")

        while True:
            build_command_question = {
                'type': 'input',
                'name': 'build_command',
                'message': "Enter your Build command:",
                'default': 'npm build'
            }

            build_command = prompt(build_command_question)['build_command']
        
            install_command_question = {
                'type': 'input',
                'name': 'install_command',
                'message': 'Enter your Install command:',
                'default': 'npm install'
            }

            install_command = prompt(install_command_question)['install_command']

            build_output_question = {
                'type': 'input',
                'name': 'build_output',
                'message': 'Enter your Output directory:',
                'default': 'build'
            }

            build_output = prompt(build_output_question)['build_output']

            # if not framework:
            #     print(f"> The specified directory {Style.BOLD}{absolute_path}{Style.RESET} has no {Style.BOLD}.html{Style.RESET} file.")
            #     sys.exit(1)
        
            print(f"{Style.GREY}- Build Command: {build_command}{Style.RESET}")
            print(f"{Style.GREY}- Install Command: {install_command}{Style.RESET}")
            print(f"{Style.GREY}- Build Output Directory: {build_output}{Style.RESET}")

            if not confirm_action(f"> {Style.CYAN}{Style.BOLD}Would you like to modify these settings?{Style.RESET}"):
                break

    start_time = time.time()
    zip_file_path = compress_directory(absolute_path, project_name)
    
    with yaspin(text=f"{Style.BOLD}Initializing Deployment...{Style.RESET}", color="cyan") as spinner:
        if framework == "html":
            workflow = deploy_local(framework, zip_file_path, email, project_name, username, "./", retrodeep_access_token)
        else:
            workflow = deploy_local(framework, zip_file_path, email, project_name, username, "./", retrodeep_access_token, install_command, build_command, build_output)

        os.remove(zip_file_path)
        if workflow.get('status') == 'completed':
            spinner.ok("✔")
        else:
            spinner.ok("x")
            sys.exit(1)

    # Check if workflow completed successfully
    with yaspin(text=f"{Style.BOLD}Finalizing Setup...{Style.RESET}", color="cyan") as spinner:
        while not is_domain_up(workflow.get('url2')):
            time.sleep(0.2)
        spinner.ok("✔")

    duration = round(time.time() - start_time, 2)
    with yaspin(text=f"{Style.BOLD}Deploy Succeeded [{duration}s]{Style.RESET}", color="cyan") as spinner:
        spinner.ok("✔")
    print(
        f"> 🔗 Your website is live at: \033[1m\x1b]8;;{workflow.get('url2')}\x1b\\{workflow.get('url')}\x1b]8;;\x1b\\\033[0m")
    print(f"> 🧪 Deployment: \033[1m\x1b]8;;{workflow.get('url3')}\x1b\\{workflow.get('url4')}\x1b]8;;\x1b\\\033[0m")
    print("> 🎉 Congratulations! Your project is now up and running.")
    sys.exit(0)


def deploy_from_repo(token, username, email, retrodeep_access_token):
    repos = list_user_repos(token)
    
    # The prompt for selecting a repository
    if repos:
        questions = [
            {
                'type': 'list',
                'name': 'repo',
                'message': 'Which repo would you like to deploy?',
                'choices': repos
            }
        ]
        answers = prompt(questions)
        repo_name = answers['repo']
        # Proceed with the selected repository
    else:
        print("You do not have any repositories")
        sys.exit(1)

    # Fetch the directories from the repository
    directories = get_repo_directories(token, username, repo_name)

    name_of_project = name_of_project_prompt_repo(repo_name, username, retrodeep_access_token)

    # Ensure './' is included as the first option to represent the root directory
    directories_with_root = ['./'] + \
        ['./' + d for d in directories if d != './']

    questions = [
        {
            'type': 'list',
            'name': 'directory',
            'message': 'Select the directory with your code:',
            'choices': directories_with_root,
            'default': './'
        }
    ]

    dir_answer = prompt(questions)
    directory = dir_answer['directory']

    start_time = time.time()

    with yaspin(text=f"{Style.BOLD}Initializing Deployment...{Style.RESET}", color="cyan") as spinner:
        # Fork the selected repository to the organization
        workflow = deploy(email, repo_name, name_of_project,
                          directory, username, retrodeep_access_token)
        if workflow.get('status') == 'completed':
            spinner.ok("✔")

    with yaspin(text=F"{Style.BOLD}Finalizing Setup...{Style.RESET}", color="cyan") as spinner:
        while not is_domain_up(workflow.get('url2')):
            time.sleep(0.2)
        spinner.ok("✔")

    duration = round(time.time() - start_time, 2)
    with yaspin(text=f"{Style.BOLD}Deploy Succeeded {Style.RESET}{Style.GREY}[{duration}s]{Style.RESET}", color="cyan") as spinner:
        spinner.ok("✔")
    print(
        f"> 🔗 Your website is live at: {Style.BOLD}{workflow.get('url2')}{Style.RESET}")
    print(f"> 🧪 Deployment: {Style.BOLD}{workflow.get('url4')}{Style.RESET}")
    print("> 🎉 Congratulations! Your project is now up and running.")

    sys.exit(0)


def init(debug=False):
    # Check for existing credentials
    credentials = get_stored_credentials()
    if credentials:
        token = credentials['access_token']
        username = credentials['username']
        email = credentials['email_address']
        retrodeep_access_token = credentials['retrodeep_access_token']

    else:
        # If no credentials, initiate OAuth
        print("> No existing Retrodeep credentials detected. Please authenticate")
        print("> Authenticate with GitHub to proceed with Retrodeep:")
        token, username, email, retrodeep_access_token = initiate_github_oauth()
        manage_user_session(username, token, email)

    try:
        print(f"Hi {username}!")
        deploy_choices = [
            {
                'type': 'list',
                'name': 'source',
                'message': 'Choose a deployment source:',
                'choices': ['Local Directory', 'GitHub Repository']
            }
        ]
        answers = prompt(deploy_choices)

        if answers['source'] == 'Local Directory':
            # Continue with the deployment process
            deploy_from_local(username, email, retrodeep_access_token)
        else:
            # Continue with the repo deployment process
            deploy_from_repo(token, username, email, retrodeep_access_token)

    except SystemExit as e:
        sys.exit(e)
    except:
        raise SystemExit()

def deploy_using_flags(args):
    credentials = get_stored_credentials()
    if credentials:
        token = credentials['access_token']
        username = credentials['username']
        email = credentials['email_address']
        retrodeep_access_token = credentials['retrodeep_access_token']
    else:
        # If no credentials, initiate OAuth
        print("> No existing Retrodeep credentials detected. Please authenticate")
        print("> Authenticate with GitHub to proceed with Retrodeep:")
        token, username, email, retrodeep_access_token = initiate_github_oauth()
        manage_user_session(username, token, email)

    absolute_path = os.path.abspath(args.directory)
    
    if not os.path.exists(absolute_path) and os.path.isdir(absolute_path):
        print(f"> The specified directory {Style.BOLD}{absolute_path}{Style.RESET} does not exist.")
        sys.exit(1)
    
    framework = check_files_and_framework(absolute_path)
    
    if not framework:
        print(f"> The specified directory {Style.BOLD}{absolute_path}{Style.RESET} has no {Style.BOLD}.html{Style.RESET} file.")
        sys.exit(1)


    if check_project_exists(username, args.name, retrodeep_access_token):
        print(f"> A project with the name {Style.BOLD}{args.name}{Style.RESET} already exists.")
        repo_name = generate_domain_name(args.name)
    else:
        repo_name = args.name

    print(f"You are about to deploy the project {Style.BOLD}{repo_name}{Style.RESET} from the directory: {Style.BOLD}{absolute_path}{Style.RESET}")
    
    if not confirm_action(f"> {Style.CYAN}{Style.BOLD}Do you want to continue?{Style.RESET}"):
        print("> Operation canceled")
        sys.exit(0)

    start_time = time.time()
    zip_file_path = compress_directory(absolute_path, args.name)
    print(zip_file_path)

    with yaspin(text=f"{Style.BOLD}Initializing Deployment...{Style.RESET}", color="cyan") as spinner:
        workflow = deploy_local(framework, zip_file_path, email, repo_name, username, "./", retrodeep_access_token)
        os.remove(zip_file_path)

        if workflow.get('status') == 'completed':
            spinner.ok("✔")
        else:
            spinner.ok("x")
            sys.exit(1)
            

    # Check if workflow completed successfully
    with yaspin(text=f"{Style.BOLD}Finalizing Setup...{Style.RESET}", color="cyan") as spinner:
        while not is_domain_up(workflow.get('url2')):
            time.sleep(0.2)
        spinner.ok("✔")

    duration = round(time.time() - start_time, 2)
    with yaspin(text=f"{Style.BOLD}Deploy Succeeded [{duration}s]{Style.RESET}", color="cyan") as spinner:
        spinner.ok("✔")
    print(
        f"> 🔗 Your website is live at: \033[1m\x1b]8;;{workflow.get('url2')}\x1b\\{workflow.get('url')}\x1b]8;;\x1b\\\033[0m")
    print(f"> 🧪 Deployment: \033[1m\x1b]8;;{workflow.get('url3')}\x1b\\{workflow.get('url4')}\x1b]8;;\x1b\\\033[0m")
    print("> 🎉 Congratulations! Your project is now up and running.")
    sys.exit(0)

def dev(args):
    credentials = get_stored_credentials()
    if credentials:
        token = credentials['access_token']
        username = credentials['username']
        email = credentials['email_address']
        retrodeep_access_token = credentials['retrodeep_access_token']
    else:
        # If no credentials, initiate OAuth
        print("> No existing Retrodeep credentials detected. Please authenticate")
        print("> Authenticate with GitHub to proceed with Retrodeep:")
        token, username, email, retrodeep_access_token = initiate_github_oauth()
        manage_user_session(username, token, email)

    if not args.port:
        port = 3000
    else:
        port = int(args.port)

    if not args.directory:
        dir = "."
    else:
        dir = args.directory

    absolute_path = os.path.abspath(dir)

    if not os.path.exists(absolute_path):
        print(f"> The specified directory {Style.BOLD}{dir}{Style.RESET} does not exist.")
        sys.exit(1)
    
    os.chdir(absolute_path)
    start_server(port, dir)

def start_server(port, dir_path):
    while True:
        try:
            with MyTCPServer(("", port), QuietHTTPRequestHandler) as httpd:
                print(f"> Hooray! Dev ready at {Style.BOLD}{Style.UNDERLINE}http://localhost:{port}{Style.RESET}")
                webbrowser.open_new_tab(f"http://localhost:{port}")
                httpd.serve_forever()
            break  
        except OSError as e:
            if e.errno in (98, 48): 
                print(f"> Port {port} is already in use")
                port += 1  
            else:
                raise 
        except KeyboardInterrupt:
            httpd.server_close()
            sys.exit(0)
        except SystemExit as e:
            httpd.server_close()
            sys.exit(e)
        except:
            httpd.server_close()
            raise SystemExit()

def logout(args):
    retrodeep_dir = os.path.join(os.path.expanduser('~'), '.retrodeep')
    if os.path.exists(retrodeep_dir):
        try:
            shutil.rmtree(retrodeep_dir)
            print("> Log out successful!")
        except Exception as e:
            print(f"Error during logout: {e}")
            sys.exit(1)
    else:
        print("> You are not currently logged in to retrodeep.")


def login(args):
    credentials = get_stored_credentials()
    if credentials:
        print(
            f"> You are currently logged in to Retrodeep with the email address {Style.BOLD}{credentials['email_address']}{Style.RESET}")
        sys.exit(1)
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
            print("> Failed to authenticate or create user.")
            sys.exit(1)

def show_help(parser):
    parser.print_help()
    sys.exit()


def login_message(email):
    print(
        f"> You have successfully authenticated with GitHub as {Style.BOLD}{email}{Style.RESET}")
    print(
        f"Welcome aboard! Enjoy your journey with Retrodeep! 🚀")


def list_projects(args):
    credentials = login_for_workflow()
    
    username = credentials['username']
    email = credentials['email_address']
    retrodeep_access_token = credentials['retrodeep_access_token']

    get_user_projects(username, retrodeep_access_token, email)


def delete_project(args):
    credentials = login_for_workflow()
    
    username = credentials['username']
    retrodeep_access_token = credentials['retrodeep_access_token']

    project_name = args.project_name
    if not project_name:
        print("Error: Project name is required.")
        parser_deleteProjects.print_help()
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


def whoami(args):
    credentials = login_for_workflow()

    username = credentials['username']
    email = credentials['email_address']

    print(f"> {Style.BOLD}{username}{Style.RESET}")
    print(
        f"> You are currently authenticated using the email address {Style.BOLD}{email}{Style.RESET}")


def get_stored_credentials():
    credentials_file = Path.home() / '.retrodeep' / 'credentials.json'
    if credentials_file.exists():
        with open(credentials_file, 'r') as file:
            return json.load(file)
    return None


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


def format_days_since(updated_at_str):
    updated_at = datetime.strptime(updated_at_str, '%a, %d %b %Y %H:%M:%S %Z')
    time_diff = datetime.utcnow() - updated_at
    days_diff = time_diff.days
    hours_diff = time_diff.seconds // 3600  # Convert seconds to hours

    if days_diff < 1:
        return f"{hours_diff}h"
    else:
        return f"{days_diff}d"


def confirm_action(prompt):
    while True:
        response = input(prompt + f" {Style.GREY}[Y/n]{Style.RESET}: ").strip().lower()
        if response in ('y', 'n', ''):
            return response == 'y'
        else:
            print("Please enter 'Y' for yes or 'N' for no.")
    else:
        sys.exit(1)

def generate_domain_name(project_name):
    return f"{project_name}-{randomname.get_name(noun=('cats', 'astronomy' 'food'))}"


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
                f'{Style.BOLD}Deployment URL{Style.RESET}': f"https://{project['domain_name']}.retrodeep.app",
                f'{Style.BOLD}Last Updated{Style.RESET}': format_days_since(project['updated_at'])
            }
            for project in projects_data
        ]
        print(f"> Projects for user {Style.BOLD}{email_address}{Style.RESET}\n")
        print(tabulate(projects_list, headers='keys', tablefmt='plain'))
    else:
        print(
            f"Failed to retrieve projects for {username}. Status Code: {response.status_code}")


def check_project_exists(username, project_name, retrodeep_access_token):
    url = f"{API_BASE_URL}/projects/{project_name}"
    headers = {'Authorization': f'Bearer {retrodeep_access_token}'}
    data = {'username': username}
    response = requests.get(url, json=data, headers=headers)

    if response.status_code == 200:
        return True
    elif response.status_code == 404:
        return False
    else:
        raise Exception(
            f"Failed to check project existence. Status Code: {response.status_code}")


def add_new_project(username, email, project_name, domain_name, repo_name, retrodeep_access_token):
    url = f"{API_BASE_URL}/projects"
    headers = {'Content-Type': 'application/json',
               'Authorization': f'Bearer {retrodeep_access_token}'}
    data = {'project_name': project_name,
            'email': email, 'repo_name': repo_name, 'domain_name': domain_name, username: 'username'}

    if repo_name:
        data['repo_name'] = repo_name

    response = requests.post(url, json=data, headers=headers)

    try:
        response_data = response.json() 
    except ValueError:
        response_data = None

    if response.status_code == 201:
        return
    else:
        print("Failed to create project.")
        if response_data:
            print(response_data)
        else:
            print("No JSON response data.")


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

def fetch_and_display_logs(args):
    credentials = login_for_workflow()
    
    username = credentials['username']
    retrodeep_access_token = credentials['retrodeep_access_token']

    project_name = args.project_name
    if not project_name:
        print("Error: Project name is required.")
        parser_deleteProjects.print_help()
        sys.exit(1)

    url = f"{API_BASE_URL}/logs/{args.project_name}"
    headers = {'Authorization': f'Bearer {retrodeep_access_token}'}

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        logs = response.json()
        print(f"> Fetched logs for deployment {project_name} for {Style.BOLD}{project_name}{Style.RESET} ")
        for log in logs:
            print(f"{Style.GREY}{log['timestamp']}{Style.RESET}  {log['message']}")
    else:
        print(f"Failed to retrieve logs: {response.status_code}")

def initiate_github_oauth():
    session_id = str(uuid.uuid4())

    webbrowser.open(
        f"{AUTH_BASE_URL}/login?session_id={session_id}")

    time.sleep(3)

    wait_for_oauth_completion(session_id)

    return poll_for_token(session_id)


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


def list_user_repos(token):
    g = Github(token)
    user = g.get_user()
    return [repo.name for repo in user.get_repos()]


def deploy(email, repo_name, project_name, directory, username, retrodeep_access_token, install_command=None, build_command=None, build_output=None):
    url = f"{DEPLOY_BASE_URL}/repo/github"
    headers = {'Authorization': f'Bearer {retrodeep_access_token}'}
    data = {
            'email': email, 
            'repo_name': repo_name,
            'project_name': project_name, 
            'directory': directory, 
            'username': username, 
            'install_command': install_command, 
            'build_command': build_command, 
            'build_output': build_output
            }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        workflow = response.json()
        return workflow
    except requests.exceptions.HTTPError as err:
        print(f"HTTP error occurred: {err}")
    except Exception as err:
        print(f"An error occurred: {err}")
    return []

def deploy_local(framework, zip_file_path, email, project_name, username, directory, retrodeep_access_token):
    url = f"{DEPLOY_BASE_URL}/local"
    headers = {'Authorization': f'Bearer {retrodeep_access_token}'}
    data = {'project_name': project_name, 'username': username, 'directory': directory, 'email': email, 'framework': framework}

    try:
        with open(zip_file_path, 'rb') as f:
            files = {'file': (os.path.basename(zip_file_path), f)}
            response = requests.post(url, data=data, files=files, headers=headers)
            response.raise_for_status()

        return response.json()
    except requests.exceptions.RequestException as e:
        # More detailed error handling
        if hasattr(e, 'response') and e.response is not None:
            try:
                # Attempt to decode JSON error message
                error_message = e.response.json()
            except ValueError:
                # Fallback if response is not in JSON format
                error_message = e.response.text
        else:
            error_message = str(e)
        return {"error": f"Request failed: {error_message}"}

def get_repo_directories(token, org_name, repo_name, path="."):
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    url = f"https://api.github.com/repos/{org_name}/{repo_name}/contents/{path}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    content = response.json()

    directories = []
    for item in content:
        if item['type'] == 'dir':
            subdir_path = f"{path}/{item['name']}" if path != "." else item['name']
            directories.append(subdir_path)
            directories.extend(get_repo_directories(
                token, org_name, repo_name, subdir_path))
    return directories

def name_of_project_prompt_repo(repo_name, username, retrodeep_access_token):

    repo_name = repo_name.replace(".", "-")

    if check_project_exists(username, repo_name, retrodeep_access_token):
            repo_name = generate_domain_name(repo_name)

    while True:
        # Prompt to choose user project
        name_of_project_question = {
            'type': 'input',
            'name': 'project_name',
            'message': 'Project Name (for subdomain):',
            'default': repo_name.lower()
        }

        name_of_project = prompt(name_of_project_question)['project_name'].lower()

        # Check if project exists
        if check_project_exists(username, name_of_project, retrodeep_access_token):
            print(f"> Project {Style.BOLD}{name_of_project}{Style.RESET} already exists, please choose a new name.")
        else:
            break

    return name_of_project

def name_of_project_prompt(username, retrodeep_access_token):

    while True:
        project_name_question = {
        'type': 'input',
        'name': 'project_name',
        'message': 'Enter the project name (for subdomain):'
    }
        project_name = prompt(project_name_question)['project_name']

        # Check if project exists
        if check_project_exists(username, project_name, retrodeep_access_token):
            print(f"> Project {Style.BOLD}{project_name}{Style.RESET} already exists, please choose a new name.")
        else:
            break

    return project_name


def is_domain_up(url):
    try:
        response = requests.get(url, timeout=10)
        return response.status_code == 200
    except requests.RequestException:
        return False


def generate_unique_code(length=4):
    """Generates a unique alphanumeric code of the given length."""
    chars = string.ascii_letters + string.digits
    while True:
        # Generate a random code
        code = ''.join(random.choices(chars, k=length))
        code = code.lower()
        # Check if the generated code is unique
        if code not in generated_codes:
            generated_codes.add(code)
            return code

def check_files_and_framework(directory):
    # Check for HTML file presence
    for file in os.listdir(directory):
        if file.endswith('.html'):
            return "html"
    
    # Check for package.json file presence
    package_json_path = os.path.join(directory, 'package.json')
    if os.path.exists(package_json_path):
        with open(package_json_path) as f:
            package_json = json.load(f)
            
            # Specify the key under which the framework is listed. For example: 'dependencies'
            framework_key = 'dependencies'  # Change this as needed
            
            if framework_key in package_json:
                # Assuming you want to check for specific frameworks listed under dependencies
                frameworks = ['react', 'vue', 'next'] 
                for framework in frameworks:
                    if framework in package_json[framework_key]:
                        return framework
    return None

def compress_directory(source_dir, output_filename):
    shutil.make_archive(output_filename, 'zip', source_dir)
    return f"{output_filename}.zip"


def Exit_gracefully(signum, frame):
    # exit(1)
    sys.exit(1)


if __name__ == "__main__":
    print(f"{Style.DIM}{Style.GREY}Retrodeep CLI {__version__}{Style.RESET}")

    signal.signal(signal.SIGINT, Exit_gracefully)

    # parser = argparse.ArgumentParser(prog='retrodeep')
    parser = argparse.ArgumentParser(prog='retrodeep', 
                                     description='Deploy. Build. Scale',
                                     formatter_class=CustomFormatter)
    # Global flags
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug')
    
    subparsers = parser.add_subparsers(title="Commands", dest="command", help="")
    parser.add_argument('-v', '--version', action='version', version=f"{__version__}")


    # Deploy command
    parser_deploy = subparsers.add_parser("deploy", help="Deploy your project from a local directory or from a git repository")    
    parser_deploy.add_argument("name", help="Name of the project")
    parser_deploy.add_argument("directory",help="Directory path for deployment")
    parser_deploy.set_defaults(func=deploy_using_flags)

    # Dev command
    parser_dev = subparsers.add_parser("dev", help="Test your project locally on your local machine")    
    parser_dev.add_argument("port", help="Port to listen on")
    parser_dev.add_argument("directory", help="Directory path for deployment")

    parser_dev.set_defaults(func=dev)

    # logs deployment command
    parser_logsProjects = subparsers.add_parser(
        "logs", help="View the logs of a deployment")
    parser_logsProjects.add_argument(
        "project_name",
        help="")
    parser_logsProjects.set_defaults(func=fetch_and_display_logs)

    # Login command
    parser_login = subparsers.add_parser(
        "login", help="Log in to Retrodeep")
    parser_login.set_defaults(func=login)

    # Logout command
    parser_logout = subparsers.add_parser(
        "logout", help="Log out of Retrodeep")
    parser_logout.set_defaults(func=logout)

    # list all deployments command
    parser_listProjects = subparsers.add_parser(
        "projects", help="List all deployments on Retrodeep")
    parser_listProjects.set_defaults(func=list_projects)

    # delete deployment command
    parser_deleteProjects = subparsers.add_parser(
        "rm", help="Delete/Remove a project on Retrodeep")
    parser_deleteProjects.add_argument(
        "project_name",
        help="Name of the project to delete")
    parser_deleteProjects.set_defaults(func=delete_project)

    # Who am i
    parser_whoami = subparsers.add_parser(
        "whoami", help="Shows the currently logged in user")
    parser_whoami.set_defaults(func=whoami)

    # help
    parser_help = subparsers.add_parser('help', help='Show help')
    parser_help.set_defaults(func=lambda args: show_help(parser))

    args = parser.parse_args()

    # if args.command == "dev":
    #     if args.port and args.dir:
    #         dev_with_flags(args)
    #     else:
    #         dev(args)

    # if args.command == "deploy":
    #     if args.name and args.directory:
    #         deploy_using_flags(args)
    #     else:
    #         init(args)

    # if hasattr(args, 'func'):
    #     args.func(args)
    # else:
    #     parser.print_help()

    # Default action if no subcommand is provided
    if not hasattr(args, 'func'):
        init(debug=args.debug)
    else:
        args.func(args)
