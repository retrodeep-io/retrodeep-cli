import argparse
import os
import signal
import sys, traceback
from yaspin import yaspin
import http.server
import socketserver
import ssl

from retrodeep.command.login.login import login

from retrodeep.command.logout.logout import logout

from retrodeep.command.dev.dev import dev
 
from retrodeep.command.deploy.deploy import deploy_using_flags 
from retrodeep.command.deploy.deploy import init 

from retrodeep.command.logs.logs import fetch_and_display_logs

from retrodeep.command.projects.projects import list_projects

from retrodeep.command.ls.ls import list_projects_deployments

from retrodeep.command.rm.rm import delete_project

from retrodeep.command.whoami.whoami import whoami

from retrodeep.command.help.help import print_custom_help
from retrodeep.command.help.help import help_command

from cryptography.fernet import Fernet

from retrodeep.version import __version__

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

ssl._create_default_https_context = ssl._create_unverified_context

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

def Exit_gracefully(signum, frame):
    # exit(1)
    sys.exit(1)

if __name__ == "__main__":

    print(f"{Style.DIM}{Style.GREY}Retrodeep CLI {__version__}{Style.RESET}")

    if "-h" in sys.argv or "--help" in sys.argv or "help" in sys.argv:
        print_custom_help()
        sys.exit()

    signal.signal(signal.SIGINT, Exit_gracefully)

    # parser = argparse.ArgumentParser(prog='retrodeep')
    parser = argparse.ArgumentParser(prog='retrodeep',
                                     add_help=False,
                                     description='Deploy. Build. Scale',
                                     formatter_class=CustomFormatter)
    # Global flags
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug')
    parser.add_argument('-v', '--version', action='version', version=f"{__version__}")

    subparsers = parser.add_subparsers(title="Commands", dest="command", help="")

    # Deploy command
    parser_deploy = subparsers.add_parser("deploy", help="Deploy your project from a local directory or from a git repository")
    # parser_deploy.add_argument("name", help="Name of the project")
    parser_deploy.add_argument("directory",help="Directory path for deployment")
    parser_deploy.set_defaults(func=deploy_using_flags)

    # Dev command
    parser_dev = subparsers.add_parser("dev", help="Test your project locally on your local machine")
    parser_dev.add_argument("-p", "--port", default='3000', help="Port to listen on")
    parser_dev.add_argument("-d", "--dir", nargs='?', default='.', help="Directory path for deployment")
    # parser_dev.add_argument("-p", "--port", help="Port to listen on")

    parser_dev.set_defaults(func=dev)

    # logs deployment command
    parser_logsProjects = subparsers.add_parser(
        "logs", help="View the logs of a deployment")
    parser_logsProjects.add_argument(
        "deployment_url",
        nargs='?',
        default=None,
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

    # list all projects command
    parser_listProjects = subparsers.add_parser(
        "projects", help="List all projects on Retrodeep")
    parser_listProjects.set_defaults(func=list_projects)

     # logs deployment command
    parser_logsProjects = subparsers.add_parser(
        "ls", help="List all deployments of a project")
    parser_logsProjects.add_argument(
        "deployment_url",
        nargs='?',
        default=None,
        help="")
    parser_logsProjects.set_defaults(func=list_projects_deployments)

    # rollout deployment command
    parser_logsProjects = subparsers.add_parser(
        "rollout", help="Build and redeploy a deployment ")
    parser_logsProjects.add_argument(
        "deployment_url",
        help="")
    parser_logsProjects.set_defaults(func=list_projects_deployments)

    # delete deployment command
    parser_deleteProjects = subparsers.add_parser(
        "rm", help="Delete/Remove a project on Retrodeep")
    parser_deleteProjects.add_argument(
        "project_name",
        nargs='?',
        default=None,
        help="Name of the project to delete")
    parser_deleteProjects.set_defaults(func=delete_project)

    # Who am i
    parser_whoami = subparsers.add_parser(
        "whoami", help="Shows the currently logged in user")
    parser_whoami.set_defaults(func=whoami)

    # help cmd command
    parser_help_command = subparsers.add_parser(
        "help", help="displays command from a command")
    parser_help_command.add_argument(
        "command",
        help="Name of the command")
    parser_help_command.set_defaults(func=help_command)

    args = parser.parse_args()

    # Default action if no subcommand is provided
    if not hasattr(args, 'func'):
        init(debug=args.debug)
    else:
        args.func(args)
