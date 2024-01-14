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
import sys
import waitress
import secrets
import uuid
from tabulate import tabulate
from yaspin import yaspin
import glob

from cryptography.fernet import Fernet

app = Flask(__name__)

API_BASE_URL = "https://api.retrodeep.com/v1"
SCM_BASE_URL = "https://scm.retrodeep.com"
AUTH_BASE_URL = "https://auth.retrodeep.com"


# ANSI escape codes for colors and styles
class Style:
    GREY = '\033[90m'
    RED = '\033[31m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'


# Set to store previously generated codes to ensure uniqueness
generated_codes = set()


# Determine the configuration directory
home = os.path.expanduser("~")
config_directory = os.path.join(home, ".retrodeep")
if not os.path.exists(config_directory):
    os.makedirs(config_directory)

KEY_FILE = os.path.join(config_directory, "encryption.key")
TOKEN_FILE = os.path.join(config_directory, "user_token.enc")


def deploy_from_local(token, username, email, retrodeep_access_token):

    project_name_question = {
        'type': 'input',
        'name': 'project_name',
        'message': 'Enter the project name (for subdomain):'
    }

    project_name = prompt(project_name_question)['project_name']

    while True:
        directory_question = {
            'type': 'input',
            'name': 'directory',
            'message': 'Enter the directory path (default: current directory):',
            'default': '.'
        }
        directory = prompt(directory_question)['directory']

        # Convert the directory to an absolute path
        absolute_path = os.path.abspath(directory)

        if directory and os.path.exists(absolute_path) and os.path.isdir(absolute_path):
            # Check for the existence of .html file
            if glob.glob(os.path.join(absolute_path, '*.html')):
                print(
                    f"You are about to deploy from the directory: \033[1m{absolute_path}\033[0m")
                break
            else:
                print("There is no index.html file in the provided path.")
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
            print("Invalid directory. Please enter a valid directory path.")

    repo_name = f"{project_name}-{username}"

    zip_file_path = compress_directory(absolute_path, project_name)

    with yaspin(text="\033[1mInitializing Deployment...\033[0m", color="cyan") as spinner:
        # Fork the selected repository to the organization
        workflow = upload_file(zip_file_path, project_name,
                               repo_name, username, "./", retrodeep_access_token)
        os.remove(zip_file_path)

        if workflow.get('status') == 'completed':
            spinner.ok("✔")

    start_time = time.time()

    # Check if workflow completed successfully
    if workflow.get('conclusion') == "success":
        with yaspin(text="\033[1mFinalizing Setup...\033[0m", color="cyan") as spinner:
            while not is_domain_up(workflow.get('url2')):
                time.sleep(0.200)
            spinner.ok("✔")

        duration = round(time.time() - start_time, 2)
        with yaspin(text=f"\033[1mDeploy Succeeded [{duration}s]\033[0m", color="cyan") as spinner:
            spinner.ok("✔")
        print(
            f"> 🔗 Your website is live at: \033[1m\x1b]8;;{workflow.get('url2')}\x1b\\{workflow.get('url')}\x1b]8;;\x1b\\\033[0m")
        print("> 🎉 Congratulations! Your project is now up and running.")
    else:
        print("\nDeployment failed.")

    add_new_project(username, email, project_name, workflow.get('domain_name'),
                    workflow.get('forked_repo_name'), retrodeep_access_token)

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
        pass

    # Fetch the directories from the repository
    directories = get_repo_directories(token, username, repo_name)

    # Prompt to choose user project
    name_of_project_question = {
        'type': 'input',
        'name': 'project_name',
        'message': 'Project Name (for subdomain):',
        'default': repo_name.lower()
    }

    name_of_project = prompt(name_of_project_question)['project_name'].lower()

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

    with yaspin(text="\033[1mInitializing Deployment...\033[0m", color="cyan") as spinner:
        # Fork the selected repository to the organization
        workflow = deploy(token, repo_name, name_of_project,
                          directory, username, retrodeep_access_token)
        if workflow.get('status') == 'completed':
            spinner.ok("✔")

    start_time = time.time()

    # Check if workflow completed successfully
    if workflow.get('conclusion') == "success":
        with yaspin(text="\033[1mFinalizing Setup...\033[0m", color="cyan") as spinner:
            while not is_domain_up(workflow.get('url2')):
                time.sleep(0.200)
            spinner.ok("✔")

        duration = round(time.time() - start_time, 2)
        with yaspin(text=f"\033[1mDeploy Succeeded [{duration}s]\033[0m", color="cyan") as spinner:
            spinner.ok("✔")
            # print(f"\nDeploy Succeeded [{duration}s]")
        print(
            f"> 🔗 Your website is live at: \033[1m\x1b]8;;{workflow.get('url2')}\x1b\\{workflow.get('url')}\x1b]8;;\x1b\\\033[0m")
        print("> 🎉 Congratulations! Your project is now up and running.")
    else:
        print("\nDeployment failed.")

    add_new_project(username, email, name_of_project, workflow.get('domain_name'),
                    workflow.get('forked_repo_name'), retrodeep_access_token)

    sys.exit(0)


def init(args):
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
        deploy_from_local(token, username, email, retrodeep_access_token)
    else:
        # Continue with the repo deployment process
        # We'll modify the deploy_from_repo function to prompt for the repo name if it's None
        deploy_from_repo(token, username, email, retrodeep_access_token)


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
            f"> You are currently logged in to Retrodeep with the email address \033[1m{credentials['email_address']}\033[0m")
        sys.exit(1)
    else:
        print("> No Credentials found. You are not currently logged in to retrodeep.")
        # Initiate GitHub OAuth process and retrieve token and email
        token, username, email, retrodeep_access_token = initiate_github_oauth()
        # If the user was successfully added or already exists, store their session
        if username and email and token and retrodeep_access_token:
            login_message(email)
            manage_user_session(username, token, email, retrodeep_access_token)
        else:
            print("> Failed to authenticate or create user.")
            sys.exit(1)


def login_for_workflow():
    credentials = get_stored_credentials()
    if credentials:
        return credentials
    else:
        print("> No Credentials found. You are not currently logged in to Retrodeep.")

        # Initiate GitHub OAuth process and retrieve token and email
        token, username, email, retrodeep_access_token = initiate_github_oauth()

        # If the user was successfully added or already exists, store their session
        if username and email and token and retrodeep_access_token:
            login_message(email)
            manage_user_session(username, token, email, retrodeep_access_token)
            credentials = get_stored_credentials()
            return credentials
        else:
            print("> Failed to authenticate or create user.")
            sys.exit(1)


def login_message(email):
    print(
        f"🎉 You have successfully authenticated with GitHub as \033[1m{email}\033[0m")
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
                f"You're about to remove the project: \033[1m{project_name}\033[0m")
            print("This would permanently delete all its deployments and dependencies")
            
            if confirm_action(f"> {Style.RED}\033[1mAre you sure?\033[0m{Style.RESET}"):
                delete_project_request(
                    username, args.project_name, retrodeep_access_token)
            else:
                print("> Operation canceled")
                sys.exit(1)
        else:
            print(
                f'> There are no deployments or projects matching \033[1m{project_name}\033[0m.')


def whoami(args):
    credentials = login_for_workflow()

    username = credentials['username']
    email = credentials['email_address']

    print(f"> \033[1m{username}\033[0m")
    print(
        f"> You are currently authenticated using the email address \033[1m{email}\033[0m")


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
        response = input(prompt + " [Y/n]: ").strip().lower()
        if response in ('y', 'n', ''):
            return response == 'y'
        else:
            print("Please enter 'Y' for yes or 'N' for no.")
    else:
        sys.exit(1)


def get_user_projects(username, retrodeep_access_token, email_address):
    url = f"{API_BASE_URL}/users/{username}/projects"
    headers = {'Authorization': f'Bearer {retrodeep_access_token}'}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        projects_data = response.json()

        if not projects_data:  # Check if the projects list is empty
            print(f"No projects found for {username}.")
            return

        projects_list = [
            {
                '\033[1mProject Name\033[0m': f" \033[1m{project['project_name']}\033[0m",
                '\033[1mDeployment URL\033[0m': f"https://{project['domain_name']}.retrodeep.com",
                '\033[1mLast Updated\033[0m': format_days_since(project['updated_at'])
            }
            for project in projects_data
        ]
        print(f"> Projects for user \033[1m{email_address}\033[0m\n")
        print(tabulate(projects_list, headers='keys', tablefmt='plain'))
    else:
        print(
            f"Failed to retrieve projects for {username}. Status Code: {response.status_code}")


def check_project_exists(username, project_name, retrodeep_access_token):
    url = f"{API_BASE_URL}/users/{username}/projects/{project_name}"
    headers = {'Authorization': f'Bearer {retrodeep_access_token}'}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return True
    elif response.status_code == 404:
        return False
    else:
        raise Exception(
            f"Failed to check project existence. Status Code: {response.status_code}")


def add_new_project(username, email, project_name, domain_name, repo_name, retrodeep_access_token):
    url = f"{API_BASE_URL}/users/{username}/projects"
    headers = {'Content-Type': 'application/json',
               'Authorization': f'Bearer {retrodeep_access_token}'}
    data = {'project_name': project_name,
            'email': email, 'repo_name': repo_name, 'domain_name': domain_name}

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
    url = f"{API_BASE_URL}/users/{username}/projects/{project_name}"
    headers = {'Authorization': f'Bearer {retrodeep_access_token}'}

    response = requests.delete(url, headers=headers)

    if response.status_code == 200:
        print(f"Bravo! Deleted 1 project \033[1m{project_name}\033[0m")
    else:
        print(
            f"Failed to delete project. Status Code: {response.status_code}")
        print(response.json())


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
            print("\n> Authentication completed.")
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


def deploy(token, repo_name, project_name, directory, username, retrodeep_access_token):
    url = f"{SCM_BASE_URL}/github/deploy"
    headers = {'Authorization': f'Bearer {retrodeep_access_token}'}
    data = {'token': token, 'repo_name': repo_name,
            'project_name': project_name, 'directory': directory, 'username': username}

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


def detect_project_type(token, repo_name, org_name):
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    url = f"https://api.github.com/repos/{org_name}/{repo_name}/contents/package.json"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        package_content = base64.b64decode(response.json()['content']).decode()
        package_json = json.loads(package_content)

        dependencies = package_json.get("dependencies", {})
        if "next" in dependencies:
            return "nextjs"
        elif "react" in dependencies and "react-dom" in dependencies:
            return "react"
    return "html"


def detect_package_manager(token, org_name, repo_name):
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    # Check for yarn.lock
    yarn_url = f"https://api.github.com/repos/{org_name}/{repo_name}/contents/yarn.lock"
    response_yarn = requests.get(yarn_url, headers=headers)

    # Check for package-lock.json
    npm_url = f"https://api.github.com/repos/{org_name}/{repo_name}/contents/package-lock.json"
    response_npm = requests.get(npm_url, headers=headers)

    if response_yarn.status_code == 200:
        return "yarn"
    elif response_npm.status_code == 200:
        return "npm"
    else:
        package_url = f"https://api.github.com/repos/{org_name}/{repo_name}/contents/package.json"
        response_package = requests.get(package_url, headers=headers)
        if response_package.status_code == 200:
            package_content = base64.b64decode(
                response_package.json()['content']).decode()
            package_json = json.loads(package_content)
            scripts = package_json.get("scripts", {})
            for script in scripts.values():
                if "yarn" in script:
                    return "yarn"
                elif "npm" in script:
                    return "npm"
    return None


def compress_directory(source_dir, output_filename):
    shutil.make_archive(output_filename, 'zip', source_dir)
    return f"{output_filename}.zip"


def upload_file(zip_file_path, project_name, repo_name, username, directory, retrodeep_access_token):
    headers = {'Authorization': f'Bearer {retrodeep_access_token}'}
    try:
        with open(zip_file_path, 'rb') as f:
            files = {'file': (os.path.basename(zip_file_path), f)}
            data = {
                'project_name': project_name,
                'repo_name': repo_name,
                'username': username,
                'directory': directory
            }
            response = requests.post(
                f"{SCM_BASE_URL}/upload", files=files, data=data, headers=headers)

        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Failed to upload. Status code: {response.status_code}"}

    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}


def Exit_gracefully(signal, frame):
    print('I have encountered the signal KILL.')
    print('CTRL+C was pressed.  Do anything here before the process exists')
    # exit(1)
    sys.exit(0)


if __name__ == "__main__":
    print(f"{Style.DIM}{Style.GREY}Retrodeep CLI 0.0.1-beta.1{Style.RESET}")

    signal.signal(signal.SIGINT, Exit_gracefully)

    parser = argparse.ArgumentParser(description="Retrodeep CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Deploy command
    parser_deploy = subparsers.add_parser(
        "deploy", help="Deploy your project locally or from a git repository")
    parser_deploy.set_defaults(func=init)

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
    # Add an argument for project name
    parser_deleteProjects.add_argument(
        "project_name",
        help="Name of the project to delete")
    parser_deleteProjects.set_defaults(func=delete_project)

    # Who am i
    parser_whoami = subparsers.add_parser(
        "whoami", help="Shows the currently logged in user")
    parser_whoami.set_defaults(func=whoami)

    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()
