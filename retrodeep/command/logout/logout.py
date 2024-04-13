import os
import shutil
import sys
from yaspin import yaspin

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

    credentials_path = os.path.join(retrodeep_dir, 'credentials.json')
    
    if os.path.isfile(credentials_path):
        try:
            with yaspin(text=f"{Style.BOLD}Logging out{Style.RESET}", color="cyan") as spinner:
              os.remove(credentials_path)
              spinner.ok("> Log out successful!")
        except Exception as e:
              spinner.fail(f"> Error during logout: {e}")
              sys.exit(1)
    else:
        print("> You are not currently logged in to retrodeep.")
