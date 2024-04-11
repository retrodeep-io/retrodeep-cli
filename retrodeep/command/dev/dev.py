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
import zipfile
from alive_progress import alive_bar
import ssl
import asyncio
import watchdog

from ..login.login import get_stored_credentials
from ..login.login import initiate_github_oauth
from ..login.login import manage_user_session

# ANSI escape codes for colors and styles
class Style:
    GREY = '\033[90m'
    RED = '\033[31m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    CYAN = '\033[36m'
    UNDERLINE = '\033[4m'


ssl._create_default_https_context = ssl._create_unverified_context

class QuietHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

class MyTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


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
        manage_user_session(username, token, email, retrodeep_access_token)

    if not args.port:
        port = 3000
    else:
        port = int(args.port)

    if not args.dir:
        dir = "."
    else:
        dir = args.dir

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