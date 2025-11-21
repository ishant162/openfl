# Copyright 2020-2024 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

"""Module with auxiliary CLI helper functions."""

import os
import re
from itertools import islice
from os import environ
from pathlib import Path
from sys import argv

from click import echo, style
from yaml import FullLoader, load

# Constants for better readability
FX_BINARY = argv[0]
TREE_SYMBOLS = {"space": "    ", "branch": "│   ", "tee": "├── ", "last": "└── "}
DEFAULT_LENGTH_LIMIT = 1000
WORKSPACE_CONFIG_FILE = ".workspace"

# Path constants
SITEPACKS = Path(__file__).parent.parent.parent.parent.parent.parent
WORKSPACE = SITEPACKS / "openfl-workspace" / "experimental" / "workflow" / "FederatedRuntime"
TUTORIALS = SITEPACKS / "openfl-tutorials"
OPENFL_USERDIR = Path.home() / ".openfl"


def pretty(dictionary):
    """Pretty-print the dictionary with aligned formatting.

    Args:
        dictionary (dict): Dictionary to print with color formatting.
    """
    if not dictionary:
        return

    max_key_length = max(map(len, dictionary.keys()))

    for key, value in dictionary.items():
        echo(style(f"{key:<{max_key_length}} : ", fg="blue") + style(f"{value}", fg="cyan"))


def print_tree(
    dir_path: Path,
    level: int = -1,
    limit_to_directories: bool = False,
    length_limit: int = DEFAULT_LENGTH_LIMIT,
):
    """Print a visual tree structure for the given directory.

    Args:
        dir_path (Path): Directory path to visualize.
        level (int): Maximum depth to traverse (-1 for unlimited).
        limit_to_directories (bool): If True, only show directories.
        length_limit (int): Maximum number of items to display.
    """
    echo("\nNew experimental workspace directory structure:")

    dir_path = Path(dir_path)  # Accept string coerceable to Path
    files_count = 0
    directories_count = 0

    def _generate_tree_lines(directory: Path, prefix: str = "", level: int = -1):
        """Generate tree structure lines recursively.

        Args:
            directory (Path): Current directory to process.
            prefix (str): Current prefix for tree formatting.
            level (int): Remaining depth to traverse.

        Yields:
            str: Formatted tree lines.
        """
        nonlocal files_count, directories_count

        if level == 0:
            return  # Stop traversing at depth limit

        # Get directory contents
        if limit_to_directories:
            contents = [item for item in directory.iterdir() if item.is_dir()]
        else:
            contents = list(directory.iterdir())

        # Create pointers for tree structure
        pointers = [TREE_SYMBOLS["tee"]] * (len(contents) - 1) + [TREE_SYMBOLS["last"]]

        for pointer, path in zip(pointers, contents):
            if path.is_dir():
                yield prefix + pointer + path.name
                directories_count += 1
                # Determine next prefix
                extension = (
                    TREE_SYMBOLS["branch"]
                    if pointer == TREE_SYMBOLS["tee"]
                    else TREE_SYMBOLS["space"]
                )
                yield from _generate_tree_lines(path, prefix=prefix + extension, level=level - 1)
            elif not limit_to_directories:
                yield prefix + pointer + path.name
                files_count += 1

    # Print root directory and tree structure
    echo(dir_path.name)
    tree_iterator = _generate_tree_lines(dir_path, level=level)

    for line in islice(tree_iterator, length_limit):
        echo(line)

    # Check if we hit the length limit
    if next(tree_iterator, None):
        echo(f"... length_limit, {length_limit}, reached, counted:")

    # Print summary
    files_info = f", {files_count} files" if files_count else ""
    echo(f"\n{directories_count} directories{files_info}")


def get_workspace_parameter(parameter_name: str) -> str:
    """Get a parameter from the workspace config file (.workspace).

    Args:
        parameter_name (str): Name of the parameter to retrieve.

    Returns:
        str: Parameter value or empty string if not found.
    """
    try:
        with open(WORKSPACE_CONFIG_FILE, "r", encoding="utf-8") as config_file:
            workspace_config = load(config_file, Loader=FullLoader)
    except FileNotFoundError:
        return ""

    # Handle case where YAML is not correctly formatted
    if not workspace_config:
        workspace_config = {}

    # Return parameter value or empty string if not found or empty
    return workspace_config.get(parameter_name, "") or ""


def check_varenv(env_var: str = "", args: dict = None) -> dict:
    """Update args dictionary with environment variable value if defined.

    Args:
        env_var (str): Environment variable name to check.
        args (dict): Dictionary to update with environment variable value.

    Returns:
        dict: Updated args dictionary.
    """
    if args is None:
        args = {}

    if env_var:
        env_value = environ.get(env_var)
        if env_value is not None:
            args[env_var] = env_value

    return args


def get_fx_path(current_path: str = "") -> str:
    """Return the absolute path to fx binary.

    Args:
        current_path (str): Current path to process.

    Returns:
        str: Path to the fx binary.

    Raises:
        AttributeError: If 'lib' pattern is not found in current_path.
    """
    lib_match = re.search("lib", current_path)
    if not lib_match:
        raise AttributeError("'lib' pattern not found in current_path")

    lib_end_index = lib_match.end()
    path_prefix = current_path[:lib_end_index]
    bin_path = re.sub("lib", "bin", path_prefix)
    fx_path = os.path.join(bin_path, "fx")

    return fx_path


def remove_line_from_file(package_name: str, filename: str) -> None:
    """Remove lines containing the specified package from the file.

    Args:
        package_name (str): Package name to search for and remove.
        filename (str): Path to the file to modify.
    """
    with open(filename, "r+", encoding="utf-8") as file:
        lines = file.readlines()
        file.seek(0)

        # Write back only lines that don't contain the package name
        for line in lines:
            if package_name not in line:
                file.write(line)

        file.truncate()


def replace_line_in_file(new_line: str, line_number: int, filename: str) -> None:
    """Replace line at specified line number with new content.

    Args:
        new_line (str): New line content to write.
        line_number (int): Zero-based line number to replace.
        filename (str): Path to the file to modify.
    """
    with open(filename, "r+", encoding="utf-8") as file:
        lines = file.readlines()
        file.seek(0)

        for idx, line in enumerate(lines):
            if idx == line_number:
                file.write(new_line)
            else:
                file.write(line)

        file.truncate()
