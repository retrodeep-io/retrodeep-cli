from setuptools import setup, find_packages
import os

def get_long_description():
    with open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md"),
        encoding="utf8",
    ) as fp:
        return fp.read()

def get_version():
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "retrodeep", "version.py"
    )
    g = {}
    with open(path) as fp:
        exec(fp.read(), g)
    return g["__version__"]

setup(
    name="retrodeep-cli",
    version=get_version(),
    description="RetroDeep CLI is a powerful, user-friendly command-line interface designed to supercharge your development workflow by enabling you to deploy, manage, and scale your applications directly from the terminal..",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    author="Ayomide Alaka-Yusuf",
    license="Your License",
    url="https://github.com/retrodeep-io/retrodeep-cli",
    project_urls={
        "Documentation": "https://docs.retrodeep.com",
        "Source code": "https://github.com/retrodeep-io/retrodeep-cli",
        "Issues": "https://github.com/retrodeep-io/retrodeep-cli/issues",
    },
    packages=find_packages(exclude=("tests",)),
    package_data={"retrodeep": ["templates/*.html"]},  # Adjust based on your actual data files
    include_package_data=True,
    python_requires=">=3.9",
    install_requires=[
        "requests>=2.31.0",
        "PyGithub>=2.2.0",
        "datetime>=5.5",
        "questionary>=2.0.1",
        "uuid>=1.30",
        "yaspin>=3.0.1",
        "randomname>=0.2.1",
        "tabulate>=0.9.0",
        "alive-progress>=3.1.5",
        "pip"
    ],
    entry_points="""
        [console_scripts]
        retrodeep=retrodeep.retrodeep:main  # Adjust the entry point to match your project structure
    """,
    extras_require={
        "test": [
            "pytest>=5.2.2",
            # Add additional testing dependencies as needed
        ],
        # Define other extras_require as needed
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        # Update classifiers as appropriate for your project
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
