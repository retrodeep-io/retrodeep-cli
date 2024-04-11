from github import Github
# from PyInquirer import prompt
from questionary import prompt
from nacl import encoding, public
import os
import shutil
from tqdm import tqdm
from datetime import datetime, timedelta
from pathlib import Path
from clint.textui import progress
import sys
from tabulate import tabulate
from yaspin import yaspin
from alive_progress import alive_bar


class Style:
    GREY = '\033[90m'
    RED = '\033[31m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    CYAN = '\033[36m'
    UNDERLINE = '\033[4m'

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
