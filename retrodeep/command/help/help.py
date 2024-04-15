from questionary import prompt
from datetime import datetime, timedelta
from pathlib import Path


__version__ = "0.0.1 Pre-Release"

class Style:
    GREY = '\033[90m'
    RED = '\033[31m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    CYAN = '\033[36m'
    UNDERLINE = '\033[4m'

def print_custom_help():
    custom_help_text = f"""
 Usage: {Style.BOLD}retrodeep{Style.RESET} [options] [command]

 Effortless deployments in seconds.

 Options:
 -h, --help            Displays usage information.
 -d, --debug           Enable debug mode [default: off]
 -v, --version         Display version no

 Commands:
 deploy                Deploy your project from a local directory or from a git repository
 dev                   Kickstart your project using a retrodeep dev server
 logs                  Display logs for a Retrodeep deployment
 login                 Log in to Retrodeep
 logout                Log out of Retrodeep
 projects              Manage your Retrodeep projects/app
 ls                    List all the deployments of a specific project
 rm                    Delete a project or a deployment on Retrodeep
 whoami                Shows the currently logged in user
 help                  Displays help
"""
    print(custom_help_text)

def help_command(args):  
    if args.command == 'deploy':
        print(
          f"""
 Usage: {Style.BOLD}retrodeep deploy{Style.RESET} [project-name] [project-path]

 Deploy your project from your local machine to Retrodeep. You can use "retrodeep"
 to choose between deploying from your repository or local machine

 options:
 -h, --help            show this help message and exit
 -d, --debug           Enable debug
 -v, --version         show program's version number and exit

 Examples:

  - Deploy from local or reppository

   $ retrodeep

 - Deploy the current directory

   $ retrodeep deploy .

 - Deploy a custom path

   $ retrodeep deploy /path/to/your/project

 - Print Deployment URL to a file

   $ retrodeep > deployment-url.txt
	    """)
    elif args.command == 'dev':
        print(
          f"""
 Usage: {Style.BOLD}retrodeep dev{Style.RESET} [dir] [port]

 Start your project using a retrodeep dev server.

 Options:
 -p, --port <port>        Specify custom port
 -d, --dir  <dir_path>    Specify custom dir path
 -h, --help               Display help

 Examples:

 - Start a dev server in the current directory

   $ retrodeep dev

 - Start a dev server in custom path

   $ retrodeep dev --dir /path/to/your/project

 - Start a dev server on a custom path e.g 3000

   $ retrodeep dev --port 3000
	    """)
    elif args.command == 'logs':
        print(
          f"""
 Usage: {Style.BOLD}retrodee logs{Style.RESET} [deployment URL | deployment ID]

 Display logs for a Retrodeep deployment.

 Options:
 -h, --help            

 Examples:

 - Show logs for a deployment using deployment url

   $ retrodeep logs example_deployment_url

	    """)
    elif args.command == 'login':
        print(
          f"""
 Usage: {Style.BOLD}retrodeep login{Style.RESET}

 Login to Retrodeep using Github Oauth.

 Options:
 -h, --help            

	    """)
    elif args.command == 'logout':
        print(
          f"""
 Usage: {Style.BOLD}retrodeep logout{Style.RESET}

Logout of Retrodeep on your local machine.

 Options:
 -h, --help            

	    """)
    elif args.command == 'projects':
        print(
          f"""
 Usage: {Style.BOLD}retrodeep projects{Style.RESET}

 Manage your Retrodeep projects

 Options:
 -h, --help            

	    """)
    elif args.command == 'ls':
        print(
          f"""
 Usage: {Style.BOLD}retrodeep ls{Style.RESET} [project] 

 List all deployments for a project/app.

 Options:
 -h, --help            

 Examples:

 - List all deployments for the project 'test-app'

   $ retrodeep ls test-app

	    """)
    elif args.command == 'rm':
        print(
          f"""
 Usage: {Style.BOLD}retrodeep rm{Style.RESET} [project] 

 Remove a project deployment via ID or name.

 Options:
 -h, --help            

 Examples:

 - Remove a project deployment with name 'test-app'

   $ retrodeep rm test-app

 - Remove a project deployment with deploymentID 

   $ retrodeep rm deploymentID 

	    """)
    elif args.command == 'whoami':
        print(
          f"""
 Usage: {Style.BOLD}retrodeep whoami{Style.RESET}

 Displays the username of the currently logged in user.

 Options:
 -h, --help            

 Examples:

 - List all deployments for the project 'test-app'

   $ retrodeep ls test-app

	    """)
    else:
      print_custom_help()

def help_command2(args):  
    if args == 'deploy':
        print(
          f"""
 Usage: {Style.BOLD}retrodeep deploy{Style.RESET} [project-name] [project-path]

 Deploy your project from your local machine to Retrodeep. You can use "retrodeep"
 to choose between deploying from your repository or local machine.

 options:
 -h, --help            show this help message and exit
 -d, --debug           Enable debug
 -v, --version         show program's version number and exit

 Examples:

  - Deploy from local or reppository

   $ retrodeep

 - Deploy the current directory

   $ retrodeep deploy .

 - Deploy a custom path

   $ retrodeep deploy /path/to/your/project

 - Print Deployment URL to a file

   $ retrodeep > deployment-url.txt
	    """)
    elif args == 'dev':
        print(
          f"""
 Usage: {Style.BOLD}retrodeep dev{Style.RESET} [dir] [port]

 Start your project using a retrodeep dev server.

 Options:
 -p, --port <port>        Specify custom port
 -d, --dir  <dir_path>    Specify custom dir path
 -h, --help               Display help

 Examples:

 - Start a dev server in the current directory

   $ retrodeep dev

 - Start a dev server in custom path

   $ retrodeep dev --dir /path/to/your/project

 - Start a dev server on a custom path e.g 3000

   $ retrodeep dev --port 3000
	    """)
    elif args == 'logs':
        print(
          f"""
 Usage: {Style.BOLD}retrodee logs{Style.RESET} [deployment URL | deployment ID]

 Display logs for a Retrodeep deployment.

 Options:
 -h, --help            

 Examples:

 - Show logs for a deployment using deployment url

   $ retrodeep logs example_deployment_url

	    """)
    elif args == 'login':
        print(
          f"""
 Usage: {Style.BOLD}retrodeep login{Style.RESET}

 Login to Retrodeep using Github Oauth.

 Options:
 -h, --help            
	    """)
    elif args == 'logout':
        print(
          f"""
 Usage: {Style.BOLD}retrodeep logout{Style.RESET}

Logout of Retrodeep on your local machine.

 Options:
 -h, --help            

	    """)
    elif args == 'projects':
        print(
          f"""
 Usage: {Style.BOLD}retrodeep projects{Style.RESET}

 Manage your Retrodeep projects

 Options:
 -h, --help            

	    """)
    elif args == 'ls':
        print(
          f"""
 Usage: {Style.BOLD}retrodeep ls{Style.RESET} [project] 

 List all deployments for a project/app.

 Options:
 -h, --help            

 Examples:

 - List all deployments for the project 'test-app'

   $ retrodeep ls test-app

	    """)
    elif args == 'rm':
        print(
          f"""
 Usage: {Style.BOLD}retrodeep rm{Style.RESET} [project] 

 Remove a project deployment via ID or name.

 Options:
 -h, --help            

 Examples:

 - Remove a project deployment with name 'test-app'

   $ retrodeep rm test-app

 - Remove a project deployment with deploymentID 

   $ retrodeep rm deploymentID 

	    """)
    elif args== 'whoami':
        print(
          f"""
 Usage: {Style.BOLD}retrodeep whoami{Style.RESET}

 Displays the username of the currently logged in user.

 Options:
 -h, --help            

 Examples:

 - List all deployments for the project 'test-app'

   $ retrodeep ls test-app

	    """)
    else:
      print_custom_help()