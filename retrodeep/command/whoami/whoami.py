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


def whoami(args):
    credentials = login_for_workflow()

    username = credentials['username']
    email = credentials['email_address']

    print(f"> {Style.BOLD}{username}{Style.RESET}")
    print(
        f"> You are currently authenticated using the email address {Style.BOLD}{email}{Style.RESET}")