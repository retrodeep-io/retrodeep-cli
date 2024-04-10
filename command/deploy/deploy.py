import requests
from flask import Flask, request
from github import Github
# from PyInquirer import prompt
from questionary import prompt
import json
import base64
from nacl import encoding, public
import os
import time
from tqdm import tqdm
from datetime import datetime, timedelta
from pathlib import Path
from clint.textui import progress
import sys, traceback
from tabulate import tabulate
from yaspin import yaspin
import glob
import randomname
import zipfile
from alive_progress import alive_bar
from requests.exceptions import HTTPError, ConnectionError, Timeout, RequestException
from math import ceil


from ..login.login import get_stored_credentials
from ..login.login import initiate_github_oauth
from ..login.login import manage_user_session
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

one_gb = 1024 ** 3

API_BASE_URL = "https://api.retrodeep.com/v1"
SSE_BASE_URL = "https://sse.retrodeep.com/stream"
AUTH_BASE_URL = "https://auth.retrodeep.com"

def deploy_from_local(username, email, retrodeep_access_token):
    """
    Deploy to Retrodeep from a local dir.

    :param username: Username of the Retrodeep user.
    :param email: email of the Retrodeep user.
    :param retrodeep_access_token: access token of Retrodeep user.
    :return: Deployment message
    """
    source = "local"

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
            dir_size = get_dir_size(absolute_path)
            if dir_size > one_gb:
                print(f"{Style.RED}Error:{Style.RESET} The file size {Style.BOLD}{dir_size}{Style.RESET} exceeds the maximum allowed size of 1GB")
                return
            # Check for the existence of .html file
            if glob.glob(os.path.join(absolute_path, '*.html')):
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
            
    project_name = name_of_project_prompt(absolute_path, username, retrodeep_access_token)

    zip_file_path = compress_directory(absolute_path, project_name)

    start_time = time.time()
    
    with yaspin(text=f"{Style.BOLD}Initializing Deployment...{Style.RESET}", color="cyan") as spinner:

        workflow = deploy_local(zip_file_path, email, project_name, source, username, "./", retrodeep_access_token)

        os.remove(zip_file_path)

        deployment_params = listen_to_sse(workflow.get('deployment_id'))
        
        if deployment_params.get("status") == "Failed":
            spinner.fail("✘")
        else:
            spinner.ok("✔")

    duration = round(time.time() - start_time, 2)
    
    if deployment_params.get("status") == "Failed":
        with yaspin(text=f"{Style.BOLD}Deploy Succeeded {Style.RESET}{Style.GREY}[{duration}s]{Style.RESET}", color="cyan") as spinner:
            spinner.fail("✘")
        print (f"{Style.RED}Error:{Style.RESET} Deployment Failed {Style.GREY}[{duration}s]{Style.RESET}")
        sys.exit(1)
    else:
        with yaspin(text=f"{Style.BOLD}Deploy Succeeded {Style.RESET}{Style.GREY}[{duration}s]{Style.RESET}", color="cyan") as spinner:
            spinner.ok("✔")
        print(
            f"> 🔗 Your website is live at: {Style.BOLD}{deployment_params['url2']}{Style.RESET}")
        print(f"> 🧪 Deployment: {Style.BOLD}{deployment_params['url4']}{Style.RESET}")
        print("> 🎉 Congratulations! Your project is now up and running.")


def deploy_from_repo(token, username, email, retrodeep_access_token):
    """
    Deploy to Retrodeep from a repository dir.

    :param token: Source control token of the user.
    :param username: Username of the Retrodeep user.
    :param email: email of the Retrodeep user.
    :param retrodeep_access_token: access token of Retrodeep user.
    :return: Deployment message
    """
    source = 'github'
    repos = list_user_repos(token)
    repo_name = display_repos_and_select(repos)

    # Fetch and select a branch from the repository
    branches = list_repo_branches(token, repo_name, username)
    if branches:
        branch_questions = [
            {
                'type': 'list',
                'name': 'branch',
                'message': 'Select the branch you want to deploy:',
                'choices': branches
            }
        ]
        branch_answers = prompt(branch_questions)
        branch_name = branch_answers['branch']
    else:
        print("No branches found in this repository.")
        sys.exit(1)

    # Fetch the directories from the repository
    directories = get_repo_directories(token, username, repo_name, branch_name)

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

    directory_contents = get_repo_directory_contents(token, username, repo_name, branch_name, strip_dot_slash(directory))

    # Check for package.json in the directory contents
    if 'package.json' in directory_contents:
        package_json_content = get_file_content(token, username, repo_name, branch_name, f"{directory}/package.json")
        project_framework = analyze_package_json(package_json_content)
    else:
        # Check for HTML files as a fallback
        html_files = [file for file in directory_contents if file.endswith('.html')]
        if html_files:
            project_framework = "html"
        else:
            print("No recognizable project type found.")
            sys.exit(1)

    if project_framework != "html":
        print(f"> Auto-detected Project Settings for {Style.BOLD}{project_framework}{Style.RESET}:")

        while True:
            build_command_question = {
                'type': 'input',
                'name': 'build_command',
                'message': "Enter your Build command:",
                'default': 'yarn build'
            }

            build_command = prompt(build_command_question)['build_command']

            install_command_question = {
                'type': 'input',
                'name': 'install_command',
                'message': 'Enter your Install command:',
                'default': 'yarn install'
            }

            install_command = prompt(install_command_question)['install_command']

            build_output_question = {
                'type': 'input',
                'name': 'build_output',
                'message': 'Enter your Output directory:',
                'default': 'out' if project_framework == "Next.js" else 'build',
            }

            build_output = prompt(build_output_question)['build_output']

            print(f"{Style.GREY}- Build Command: {build_command}{Style.RESET}")
            print(f"{Style.GREY}- Install Command: {install_command}{Style.RESET}")
            print(f"{Style.GREY}- Build Output Directory: {build_output}{Style.RESET}")

            if not confirm_action(f"> {Style.CYAN}{Style.BOLD}Would you like to modify these settings?{Style.RESET}"):
                break

    start_time = time.time()

    with yaspin(text=f"{Style.BOLD}Initializing Deployment...{Style.RESET}", color="cyan") as spinner:
        # Fork the selected repository to the organization
        if project_framework == "html":
            workflow = deploy(email, repo_name, branch_name, name_of_project,
                          directory, project_framework, source, username, retrodeep_access_token)
        else:
            workflow = deploy(email, repo_name, branch_name, name_of_project,
                          directory, project_framework, source, username, retrodeep_access_token, install_command,build_command, build_output)

        deployment_params = listen_to_sse(workflow.get('deployment_id'))
        
        if deployment_params.get("status") == "Failed":
            spinner.fail("✘")
        else:
            spinner.ok("✔")

    duration = round(time.time() - start_time, 2)

    if deployment_params.get("status") == "Failed":
        with yaspin(text=f"{Style.BOLD}Deploy Succeeded {Style.RESET}{Style.GREY}[{duration}s]{Style.RESET}", color="cyan") as spinner:
            spinner.fail("✘")
        print (f"{Style.RED}Error:{Style.RESET} Deployment Failed {Style.GREY}[{duration}s]{Style.RESET}")
        sys.exit(1)
    else:
        with yaspin(text=f"{Style.BOLD}Deploy Succeeded {Style.RESET}{Style.GREY}[{duration}s]{Style.RESET}", color="cyan") as spinner:
            spinner.ok("✔")
        print(
            f"> 🔗 Your website is live at: {Style.BOLD}{deployment_params['url2']}{Style.RESET}")
        print(f"> 🧪 Deployment: {Style.BOLD}{deployment_params['url4']}{Style.RESET}")
        print("> 🎉 Congratulations! Your project is now up and running.")

def init(debug=False):
    # Check for existing credentials
    credentials = get_stored_credentials()
    if credentials:
        token = credentials['access_token']
        username = credentials['username']
        email = credentials['email_address']
        retrodeep_access_token = credentials['retrodeep_access_token']
    else:
        credentials = login_for_workflow()
        token = credentials.get("access_token")
        username = credentials.get("username")
        email = credentials.get("email")
        retrodeep_access_token = credentials.get("retrodeep_access_token")

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

    except ConnectionError:
        print(f"{Style.RED}Error:{Style.RESET} Failed to deploy due to network issues. Please check your internet connection.")
    except TimeoutError:
        print(f"{Style.RED}Error:{Style.RESET} The deployment process timed out. Please try again later.")
    except SystemExit as e:
        # print(f"Exiting: {e}")
        # turn the above line off to not print error
        sys.exit(e)
    except Exception as e:
        # traceback.print_exc()  # This will print the stack trace of the exception
        # turn the above line off to not print error
        sys.exit(1)  # Exit after printing the error details
    except:
        raise SystemExit()

def deploy_using_flags(args):
    source = "local"

    credentials = login_for_workflow()
    token = credentials['access_token']
    username = credentials['username']
    email = credentials['email_address']
    retrodeep_access_token = credentials['retrodeep_access_token']


    absolute_path = os.path.abspath(args.directory)

    if  os.path.exists(absolute_path) == False and os.path.isdir(absolute_path) == False:
        print(f"> The specified directory {Style.BOLD}{absolute_path}{Style.RESET} does not exist.")
        sys.exit(1)
    
    if args.directory and os.path.exists(absolute_path) and os.path.isdir(absolute_path):
            dir_size = get_dir_size(absolute_path)
            if dir_size > one_gb:
                print(f"{Style.RED} Error:{Style.RESET} The file size {Style.BOLD}{dir_size}{Style.RESET} exceeds the maximum allowed size of 1GB")
                sys.exit(1)

    framework = check_files_and_framework_local(absolute_path)

    if not framework:
        print(f"> The specified directory {Style.BOLD}{absolute_path}{Style.RESET} has no {Style.BOLD}.html{Style.RESET} file.")
        sys.exit(1)

    dir_name = os.path.basename(os.path.normpath(absolute_path))
    
    if check_project_exists(username, dir_name, retrodeep_access_token):
        print(f"> A project with the name {Style.BOLD}{dir_name}{Style.RESET} already exists.")
        project_name = generate_domain_name(dir_name)
    else:
        project_name = dir_name

    if glob.glob(os.path.join(absolute_path, '*.html')):
        print(f"> You are about to deploy the project {Style.BOLD}{project_name}{Style.RESET} from the directory: {Style.BOLD}{absolute_path}{Style.RESET}")
    else:
        print("> There is no .html file in the provided path.")
        sys.exit(1)
    
    if not confirm_action(f"> {Style.CYAN}{Style.BOLD}Do you want to continue?{Style.RESET}"):
        print("> Operation canceled")
        sys.exit(0)

    zip_file_path = compress_directory(absolute_path, dir_name)

    start_time = time.time()

    with yaspin(text=f"{Style.BOLD}Initializing Deployment...{Style.RESET}", color="cyan") as spinner:

        workflow = deploy_local(zip_file_path, email, project_name, source, username, "./", retrodeep_access_token)

        os.remove(zip_file_path)

        deployment_params = listen_to_sse(workflow.get('deployment_id'))
        
        if deployment_params.get("status") == "Failed":
            spinner.fail("✘")
        else:
            spinner.ok("✔")
    
    duration = round(time.time() - start_time, 2)

    if deployment_params.get("status") == "Failed":
        with yaspin(text=f"{Style.BOLD}Deploy Succeeded {Style.RESET}{Style.GREY}[{duration}s]{Style.RESET}", color="cyan") as spinner:
            spinner.fail("✘")
        print (f"{Style.RED}Error:{Style.RESET} Deployment Failed {Style.GREY}[{duration}s]{Style.RESET}")
        sys.exit(1)
    else:
        with yaspin(text=f"{Style.BOLD}Deploy Succeeded {Style.RESET}{Style.GREY}[{duration}s]{Style.RESET}", color="cyan") as spinner:
            spinner.ok("✔")
        print(
            f"> 🔗 Your website is live at: {Style.BOLD}{deployment_params['url2']}{Style.RESET}")
        print(f"> 🧪 Deployment: {Style.BOLD}{deployment_params['url4']}{Style.RESET}")
        print("> 🎉 Congratulations! Your project is now up and running.")

def get_dir_size(path):
    """Calculate the total size of all files in the specified directory."""
    total_size = 0
    for root, dirs, files in os.walk(path):
        for file in files:
            filepath = os.path.join(root, file)
            # Skip if it is symbolic link
            if not os.path.islink(filepath):
                total_size += os.path.getsize(filepath)
    return total_size

def name_of_project_prompt(absolute_path, username, retrodeep_access_token):

    dir_name = os.path.basename(os.path.normpath(absolute_path))

    if check_project_exists(username, dir_name, retrodeep_access_token):
        dir_name = generate_domain_name(dir_name)

    while True:
        project_name_question = {
        'type': 'input',
        'name': 'project_name',
        'message': f'Enter the project name (for subdomain):',
        'default': f'{dir_name}'
    }
        project_name = prompt(project_name_question)['project_name']
        
        if not project_name:
            project_name = dir_name

        # Check if project exists
        if check_project_exists(username, project_name, retrodeep_access_token):
            print(f"> Project {Style.BOLD}{project_name}{Style.RESET} already exists, please choose a new name.")
        else:
            break

    return project_name

def compress_directory(source_dir, output_filename):
    # List all files in the directory to be compressed to determine the total for the progress bar
    file_paths = []
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            file_path = os.path.join(root, file)
            file_paths.append(file_path)

    # Create a zip file with zip64 enabled
    with zipfile.ZipFile(f"{output_filename}.zip", 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as zipf, alive_bar(len(file_paths), title=f"> {Style.BOLD}Compressing and uploading files...{Style.RESET}") as bar:
        for file_path in file_paths:
            # Create a relative path for files to keep the directory structure
            relative_path = os.path.relpath(file_path, source_dir)
            zipf.write(file_path, relative_path)
            bar()  # Update the progress bar for each file processed

    return f"{output_filename}.zip"

def deploy_local(zip_file_path, email, project_name, source, username, directory, retrodeep_access_token, install_command=None, build_command=None, build_output=None):
    url = f"{API_BASE_URL}/deploy"
    headers = {'Authorization': f'Bearer {retrodeep_access_token}'}
    data = {'project_name': project_name, 'username': username, 'directory': directory, 'email': email, "source": source}

    with open(zip_file_path, 'rb') as f:
        encoded_zip = base64.b64encode(f.read()).decode('utf-8')

    data['encoded_file'] = encoded_zip

    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        if response.status_code == 202:
            return response.json()
    except HTTPError as http_err:
        print(f"{Style.RED}Error:{Style.RESET} HTTP error occurred: {http_err} - {response.status_code}")
    except ConnectionError:
        print(f"{Style.RED}Error:{Style.RESET} Connection error: Please check your internet connection.")
    except Timeout:
        print(f"{Style.RED}Error:{Style.RESET} Timeout error: The request timed out. Please try again later.")
    except requests.exceptions.RequestException as err:
        print(f"{Style.RED}Error:{Style.RESET} Request error: {err}")

def listen_to_sse(deployment_id):
    url = f"{SSE_BASE_URL}/{deployment_id}"  # Adjust the URL as needed based on your server configuration
    try:
        with requests.get(url, stream=True) as response:
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith('data:'):
                        data = decoded_line.split("data: ", 1)[1]
                        # # elif "log" in data:
                        # #     # Assuming log entries are wrapped in {"log": "message"}
                        # #     log_data = json.loads(data)
                        # #     print(log_data.get("log"))  # Print log messages continuously
                        # else:
                        return json.loads(data)
    except HTTPError as http_err:
        print(f"{Style.RED}Error:{Style.RESET} HTTP error occurred: {http_err} - {response.status_code}")
    except ConnectionError:
        print(f"{Style.RED}Error:{Style.RESET} Connection error: Please check your internet connection.")
    except Timeout:
        print(f"{Style.RED}Error:{Style.RESET} Timeout error: The request timed out. Please try again later.")  
    except Exception as e:
        print(f"An error occurred: {e}")
        return {"error": str(e)}
    except KeyboardInterrupt:
        print("Operation Canceled.")

def paginate_repos(repos, page, per_page=10):
    start = (page - 1) * per_page
    end = start + per_page
    return repos[start:end]

def display_repos_and_select(repos):
    page = 1
    per_page = 10
    total_items = len(repos)
    selected_repo = None

    while True:
        # Calculate start and end indices for the current page
        start_index = (page - 1) * per_page + 1
        end_index = start_index + per_page - 1
        if end_index > total_items:
            end_index = total_items

        paginated_repos = paginate_repos(repos, page, per_page)
        for i, repo in enumerate(paginated_repos, start=1):
            print(f"{Style.GREY}{i}{Style.RESET} {repo}")
        
        print(f"{Style.GREY}Showing Items {start_index}-{end_index} of {total_items}{Style.RESET}")

        repo_choice_question = {
            'type': 'input',
            'name': 'repo_choice',
            'message': 'Enter a number to select a repo, <n> for next, <p> for previous, <q> to quit or <s> to search:',
        }
        user_input = prompt(repo_choice_question)['repo_choice']
        user_input = user_input.lower()
        
        if user_input.isdigit():
            repo_index = int(user_input) - 1
            if repo_index >= 0 and repo_index < len(paginated_repos):
                selected_repo = paginated_repos[repo_index]
                print(f"> You have selected the repository: {Style.BOLD}{selected_repo}{Style.RESET}")
                break
            else:
                print("Invalid selection. Please try again.")
        elif user_input == 'n':
            if page * per_page < len(repos):
                page += 1
            else:
                print("You are on the last page.")
        elif user_input == 'p':
            if page > 1:
                page -= 1
            else:
                print("You are on the first page.")
        elif user_input == 's':
            selected_repo = search_and_select_repo(repos)
            break
        elif user_input == 'q':
            break

    return selected_repo


def search_and_select_repo(repos):
    while True:
        # search_term = input("Enter a search term (or leave empty to see all repositories): ")

        search_repo_question = {
            'type': 'input',
            'name': 'search_repo_choice',
            'message': 'Enter a search term (or leave empty to see all repositories):',
        }

        search_term = prompt(search_repo_question)['search_repo_choice']
        
        filtered_repos = [repo for repo in repos if search_term.lower() in repo.lower()] if search_term else None
        
        if not filtered_repos:
            print("No repositories found. Try again.")
            continue

        for i, repo in enumerate(filtered_repos, start=1):
            print(f"{Style.GREY}{i}{Style.RESET} {repo}")
        
        # repo_input = input("Enter a number to select a repo, or 'r' to refine your search: ").lower()

        search_repo_question2 = {
            'type': 'input',
            'name': 'search_repo_choice2',
            'message': 'Enter a search term (or leave empty to see all repositories):',
        }

        repo_input = prompt(search_repo_question2)['search_repo_choice2']

        if repo_input.isdigit():
            repo_index = int(repo_input) - 1
            if 0 <= repo_index < len(filtered_repos):
                selected_repo = filtered_repos[repo_index]
                print(f"You have selected the repository: {Style.BOLD}{selected_repo}{Style.RESET}")
                return selected_repo
            else:
                print("> Invalid selection. Please try again.")
        elif repo_input == 'r':
            continue
        else:
            print("> Invalid input. Please try again or refine your search.")

def list_user_repos(token):
    g = Github(token)
    user = g.get_user()
    return [repo.name for repo in user.get_repos()]

def list_repo_branches(token, repo_name, username):
    g = Github(token)
    repo_full_name = f"{username}/{repo_name}"
    repo = g.get_repo(repo_full_name)
    return [branch.name for branch in repo.get_branches()]

def get_repo_directories(token, org_name, repo_name, branch_name, path="."):
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    url = f"https://api.github.com/repos/{org_name}/{repo_name}/contents/{path}?ref={branch_name}"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        content = response.json()

        directories = []
        for item in content:
            if item['type'] == 'dir':
                subdir_path = f"{path}/{item['name']}" if path != "." else item['name']
                directories.append(subdir_path)
                directories.extend(get_repo_directories(
                    token, org_name, repo_name, branch_name, subdir_path))
        return directories
    except HTTPError as http_err:
        print(f"{Style.RED}Error:{Style.RESET} HTTP error occurred: {http_err} - {response.status_code}")
    except ConnectionError:
        print(f"{Style.RED}Error:{Style.RESET} Connection error: Please check your internet connection.")
    except Timeout:
        print(f"{Style.RED}Error:{Style.RESET} Timeout error: The request timed out. Please try again later.")
    except requests.exceptions.RequestException as err:
        print(f"Request error: {err}")

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

def get_repo_directory_contents(token, username, repo_name, branch_name, directory_path):
    """
    Fetch the contents of a directory in a GitHub repository.

    :param token: GitHub API token for authentication
    :param username: Username of the repository owner
    :param repo_name: Name of the repository
    :param branch_name: Name of the branch
    :param directory_path: Path to the directory within the repository
    :return: A list of filenames in the specified directory
    """
    # Format the GitHub API URL for the contents endpoint
    api_url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{directory_path}?ref={branch_name}"

    # Include the token in the request headers for authentication
    headers = {'Authorization': f'token {token}'}

    # Make the request to the GitHub API
    response = requests.get(api_url, headers=headers)

    # Check if the request was successful
    if response.status_code == 200:
        directory_contents = response.json()

        # Extract the name of each item in the directory
        filenames = [item['name'] for item in directory_contents]
        return filenames
    else:
        print(f"Failed to fetch directory contents: {response.status_code}")
        return []
    
def get_file_content(token, username, repo_name, branch_name, file_path):
    """
    Fetch the content of a file from a GitHub repository.

    :param token: GitHub API token for authentication.
    :param username: Username of the repository owner.
    :param repo_name: Name of the repository.
    :param branch_name: Name of the branch.
    :param file_path: Path to the file within the repository, including the filename.
    :return: The content of the file as a string.
    """
    # Format the GitHub API URL for the contents endpoint, including the file path
    api_url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{file_path}?ref={branch_name}"

    # Include the token in the request headers for authentication
    headers = {'Authorization': f'token {token}'}

    # Make the request to the GitHub API
    response = requests.get(api_url, headers=headers)

    # Check if the request was successful
    if response.status_code == 200:
        file_content = response.json()

        # Decode the file content from base64
        decoded_content = base64.b64decode(file_content['content']).decode('utf-8')
        return decoded_content
    else:
        print(f"Failed to fetch file content: {response.status_code}")
        return None

def analyze_package_json(package_json_content):
    # This function would parse the package.json content and return a string indicating the project framework
    package_json = json.loads(package_json_content)
    if 'next' in package_json.get('dependencies', {}):
        return "Next.js"
    elif 'react' in package_json.get('dependencies', {}):
        return "Create React App"
    # Add more framework checks as needed
    return "Unknown"

def confirm_action(prompt):
    while True:
        response = input(prompt + f" {Style.GREY}[Y/n]{Style.RESET}: ").strip().lower()
        if response in ('y', 'n', ''):
            return response == 'y'
        else:
            print("Please enter 'Y' for yes or 'N' for no.")
    else:
        sys.exit(1)

def deploy(email, repo_name, branch, project_name, directory, framework, source, username, retrodeep_access_token, install_command=None, build_command=None, build_output=None):
    url = f"{API_BASE_URL}/deploy"
    headers = {'Authorization': f'Bearer {retrodeep_access_token}'}
    data = {
            'email': email,
            'repo_name': repo_name,
            'branch': branch,
            'project_name': project_name,
            'directory': directory,
            'username': username,
            'install_command': install_command,
            'build_command': build_command,
            'build_output': build_output,
            'framework': framework,
            'source': source
            }

    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)  # Adjusted timeout
        if response.status_code == 202:  # Assuming 202 Accepted as the queueing response
            return response.json()
    except HTTPError as http_err:
        print(f"{Style.RED}Error:{Style.RESET} HTTP error occurred: {http_err} - {response.status_code}")
    except ConnectionError:
        print(f"{Style.RED}Error:{Style.RESET} Connection error: Please check your internet connection.")
    except Timeout:
        print(f"{Style.RED}Error:{Style.RESET} Timeout error: The request timed out. Please try again later.")
    except requests.exceptions.RequestException as err:
        print(f"Request error: {err}")

def check_files_and_framework_local(directory):
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

def check_project_exists(username, project_name, retrodeep_access_token):
    url = f"{API_BASE_URL}/projects/{project_name}"
    headers = {'Authorization': f'Bearer {retrodeep_access_token}'}
    data = {'username': username}
    try:
        response = requests.get(url, json=data, headers=headers)

        if response.status_code == 200:
            return True
        elif response.status_code == 404:
            return False
    except HTTPError as http_err:
        print(f"HTTP error occurred: {http_err} - {response.status_code}")
    except ConnectionError:
        print(f"{Style.RED}Error:{Style.RESET} Connection error: Please check your internet connection.")
    except Timeout:
        print(f"{Style.RED}Error:{Style.RESET} Timeout error: The request timed out. Please try again later.")
    except requests.exceptions.RequestException as err:
        print(f"{Style.RED}Error:{Style.RESET} Request error: {err}")
    
def generate_domain_name(project_name):
    return f"{project_name}-{randomname.get_name(noun=('cats', 'astronomy', 'food'))}"

def strip_dot_slash(input_string):
    return input_string.replace("./", "")