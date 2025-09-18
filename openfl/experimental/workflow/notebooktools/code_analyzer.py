# Copyright 2020-2025 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

import ast
import inspect
import re
import sys
from importlib import import_module
from pathlib import Path
from typing import Any, Dict, List, Optional

import nbformat
from nbdev.export import nb_export

# Constants for better readability
DEFAULT_EXP_PATTERN = r"#\s*\|\s*default_exp\s+(\w+)"
RUNTIME_CLASS_NAME = "FederatedRuntime"
RUN_METHOD_PATTERN = ".run()"
MAGIC_COMMANDS = ("!", "%")
EXCLUDE_PARAMS = ("self", "args", "kwargs")


class CodeAnalyzer:
    """Analyzes and processes Jupyter Notebooks.

    Provides code extraction and transformation functionality for converting
    Jupyter notebooks to Python scripts with federated learning specific modifications.

    Attributes:
        script_name (str): Name of the generated Python script.
        script_path (Path): Absolute path to the Python script generated.
        requirements (List[str]): List of pip libraries found in the script.
        exported_script_module (ModuleType): The imported module object of the generated script.
        available_modules_in_exported_script (list): List of available attributes in the
            exported script.
    """

    def __init__(self, notebook_path: Path, output_path: Path) -> None:
        """Initialize CodeAnalyzer and process the script from notebook.

        Args:
            notebook_path (Path): Path to Jupyter notebook to be converted.
            output_path (Path): The directory where the converted Python script will be saved.
        """
        print("Converting jupyter notebook to python script...")

        # Extract the export filename from the notebook
        self.script_name = self._get_experiment_name(notebook_path)

        # Convert the notebook to a Python script and set the script path
        script_output_dir = output_path.joinpath("src")
        script_filename = f"{self.script_name}.py"
        self.script_path = Path(
            self._convert_notebook_to_python(notebook_path, script_output_dir, script_filename)
        ).resolve()

        self.requirements = self._get_requirements()
        self._modify_experiment_script()

    def _get_experiment_name(self, notebook_path: Path) -> str:
        """Extract experiment name from Jupyter notebook.

        Looks for '#| default_exp <name>' pattern in code cells
        and extracts the experiment name. The name must be a valid Python identifier.

        Args:
            notebook_path (Path): Path to Jupyter notebook.

        Returns:
            str: The experiment name extracted from the notebook.

        Raises:
            ValueError: If no default_exp marker is found in the notebook.
        """
        with notebook_path.open("r") as notebook_file:
            notebook_content = nbformat.read(notebook_file, as_version=nbformat.NO_CONVERT)

        for cell in notebook_content.cells:
            if cell.cell_type == "code":
                code = cell.source
                match = re.search(DEFAULT_EXP_PATTERN, code)
                if match:
                    experiment_name = match.group(1)
                    print(f"Retrieved {experiment_name} from default_exp")
                    return experiment_name

        raise ValueError(
            "The notebook does not contain a '#| default_exp <experiment_name>' marker. "
            "Please add the marker to the first cell of the notebook"
        )

    def _convert_notebook_to_python(
        self, notebook_path: Path, output_path: Path, export_filename: str
    ) -> Path:
        """Convert a Jupyter notebook to a Python script.

        Args:
            notebook_path (Path): The path to the Jupyter notebook file to be converted.
            output_path (Path): The directory where the exported Python script should be saved.
            export_filename (str): The name of the exported Python script file.

        Returns:
            Path: The path to the exported Python script file.
        """
        nb_export(notebook_path, output_path)
        return Path(output_path).joinpath(export_filename).resolve()

    def _modify_experiment_script(self) -> None:
        """Modify the generated Python script by commenting out specific code.

        Comments out the following:
        - Occurrences of .run() method calls
        - Instances of FederatedRuntime class
        """
        instantiation_info = self._extract_class_instantiation_info(RUNTIME_CLASS_NAME)
        instance_names = instantiation_info.get("instance_name", [])

        # Read the script content, excluding Jupyter magic commands
        with open(self.script_path, "r") as file:
            script_content = "".join(
                line for line in file if not line.lstrip().startswith(MAGIC_COMMANDS)
            )

        # Apply modifications
        script_content = self._comment_flow_execution(script_content)
        script_content = self._comment_class_instance(script_content, instance_names)

        # Write the modified content back
        with open(self.script_path, "w") as file:
            file.write(script_content)

    def _comment_class_instance(self, script_code: str, instance_names: List[str]) -> str:
        """Comment out specified class instances in the provided script.

        Args:
            script_code (str): Script content to be analyzed.
            instance_names (List[str]): The names of the instances to comment out.

        Returns:
            str: The updated script with the specified instance lines commented out.
        """
        tree = ast.parse(script_code)
        lines = script_code.splitlines()
        lines_to_comment = set()

        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.Expr)):
                # Check if any subnode references our target instance names
                if any(
                    isinstance(subnode, ast.Name) and subnode.id in instance_names
                    for subnode in ast.walk(node)
                ):
                    # Add all lines from this node to the comment set
                    for line_idx in range(node.lineno - 1, node.end_lineno):
                        lines_to_comment.add(line_idx)

        # Comment out the identified lines
        modified_lines = [
            f"# {line}" if idx in lines_to_comment else line for idx, line in enumerate(lines)
        ]

        return "\n".join(modified_lines)

    def _comment_flow_execution(self, script_code: str) -> str:
        """Comment out lines containing '.run()' in the specified Python script.

        Args:
            script_code (str): Script content to be analyzed.

        Returns:
            str: The modified script with run statements commented out.
        """
        lines = script_code.splitlines()

        for idx, line in enumerate(lines):
            stripped_line = line.strip()
            # Comment out lines that contain .run() and are not already commented
            if not stripped_line.startswith("#") and RUN_METHOD_PATTERN in stripped_line:
                lines[idx] = f"# {line}"

        return "\n".join(lines)

    def _import_generated_script(self) -> None:
        """Import the generated Python script using the importlib module.

        Raises:
            ImportError: If the script cannot be imported.
        """
        try:
            sys.path.append(str(self.script_path.parent))
            self.exported_script_module = import_module(self.script_name)
            self.available_modules_in_exported_script = dir(self.exported_script_module)
        except ImportError as e:
            raise ImportError(f"Failed to import script {self.script_name}: {e}") from e

    def _get_class_arguments(self, class_name: str) -> List[str]:
        """Get expected class arguments for the given class name.

        Args:
            class_name (str): The name of the class.

        Returns:
            List[str]: A list of expected class arguments.

        Raises:
            NameError: If the class is not found in the exported script.
        """
        if not hasattr(self, "exported_script_module"):
            self._import_generated_script()

        # Find class from imported python script module
        target_class = None
        for attr_name in self.available_modules_in_exported_script:
            if attr_name == class_name:
                target_class = getattr(self.exported_script_module, attr_name)
                break

        if target_class is None:
            raise NameError(f"{class_name} not found.")

        if inspect.isclass(target_class):
            if "__init__" in target_class.__dict__:
                init_signature = inspect.signature(target_class.__init__)
                # Extract parameter names (excluding 'self', 'args', and 'kwargs')
                arg_names = [
                    param_name
                    for param_name in init_signature.parameters
                    if param_name not in EXCLUDE_PARAMS
                ]
                return arg_names
            return []

        print(f"{target_class} is not a class")
        return []

    def _get_class_name(self, parent_class) -> Optional[str]:
        """Find and return the name of a class derived from the provided parent class.

        Args:
            parent_class: FLSpec instance or parent class to search for.

        Returns:
            Optional[str]: The name of the derived class.

        Raises:
            ValueError: If no flow class is found that inherits from the parent class.
        """
        if not hasattr(self, "exported_script_module"):
            self._import_generated_script()

        # Go through all attributes in imported python script
        for attr_name in self.available_modules_in_exported_script:
            attribute = getattr(self.exported_script_module, attr_name)
            if (
                inspect.isclass(attribute)
                and attribute != parent_class
                and issubclass(attribute, parent_class)
            ):
                return attr_name

        raise ValueError("No flow class found that inherits from FLSpec")

    def _extract_class_instantiation_info(self, class_name: str) -> Dict[str, Any]:
        """Extract the instance name and initialization arguments for the given class.

        Args:
            class_name (str): The name of the class to search for.

        Returns:
            Dict[str, Any]: A dictionary containing 'args', 'kwargs', and 'instance_name'.
        """
        instantiation_info = {"args": {}, "kwargs": {}, "instance_name": []}

        # Read script content, excluding Jupyter magic commands
        with open(self.script_path, "r") as file:
            script_content = "".join(
                line for line in file if not line.lstrip().startswith(MAGIC_COMMANDS)
            )

        tree = ast.parse(script_content)

        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Assign)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == class_name
            ):
                # Extract instance names
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        instantiation_info["instance_name"].append(target.id)

                # Extract arguments
                instantiation_info["args"] = self._extract_positional_args(node.value.args)
                instantiation_info["kwargs"] = self._extract_keyword_args(node.value.keywords)

        return instantiation_info

    def _extract_positional_args(self, args) -> Dict[str, Any]:
        """Extract positional arguments from the AST nodes.
        Args:
            args: AST nodes representing the arguments.

        Returns:
            Dict[str, Any]: Dictionary of argument names and their values.
        """
        positional_args = {}
        for arg in args:
            if isinstance(arg, ast.Name):
                positional_args[arg.id] = arg.id
            elif isinstance(arg, ast.Constant):
                positional_args[arg.s] = ast.unparse(arg)
            else:
                positional_args[arg.arg] = ast.unparse(arg).strip()
        return positional_args

    def _extract_keyword_args(self, keywords) -> Dict[str, Any]:
        """Extract keyword arguments from the AST nodes.
        Args:
            keywords: AST nodes representing the keyword arguments.

        Returns:
            Dict[str, Any]: Dictionary of keyword argument names and their values.
        """
        keyword_args = {}
        for kwarg in keywords:
            value = ast.unparse(kwarg.value).strip()
            value = self._clean_value(value)
            try:
                value = ast.literal_eval(value)
            except ValueError:
                pass
            keyword_args[kwarg.arg] = value
        return keyword_args

    def _clean_value(self, value: str) -> str:
        """Clean the value by removing unnecessary parentheses or brackets.
        Args:
            value (str): The string value to be cleaned.

        Returns:
            str: The cleaned string value
        """
        if value.startswith("(") and "," not in value:
            value = value.lstrip("(").rstrip(")")
        if value.startswith("[") and "," not in value:
            value = value.lstrip("[").rstrip("]")
        return value

    def _get_requirements(self) -> List[str]:
        """Extract pip libraries from the script.

        Returns:
            List[str]: List of pip libraries found in the script.
        """
        requirements = []

        with self.script_path.open("r") as file:
            script_lines = file.readlines()

        for line in script_lines:
            stripped_line = line.strip()

            # Look for pip install commands
            if "pip install" in stripped_line:
                # Skip commented lines, requirements files, and OpenFL git installations
                is_commented = stripped_line.startswith("#")
                is_requirements_file = "-r" in stripped_line
                is_openfl_git = "openfl.git" in stripped_line

                if not (is_commented or is_requirements_file or is_openfl_git):
                    # Extract the package name (last part after 'pip install')
                    package_name = stripped_line.split(" ")[-1].strip()
                    requirements.append(f"{package_name}\n")

        return requirements

    def get_flow_class_details(self, parent_class) -> Dict[str, Any]:
        """Retrieve details of a flow class that inherits from the given parent class.

        Args:
            parent_class: The parent class (FLSpec instance).

        Returns:
            Dict[str, Any]: A dictionary containing:
                - flow_class_name (str): The name of the flow class.
                - expected_args (List[str]): The expected arguments for the flow class.
                - init_args (Dict[str, Any]): The initialization arguments for the flow class.
        """
        flow_class_name = self._get_class_name(parent_class)
        expected_arguments = self._get_class_arguments(flow_class_name)
        init_args = self._extract_class_instantiation_info(flow_class_name)

        return {
            "flow_class_name": flow_class_name,
            "expected_args": expected_arguments,
            "init_args": init_args,
        }

    def fetch_flow_configuration(self, flow_details: Dict[str, Any]) -> Dict[str, Any]:
        """Get flow configuration from flow details.

        Args:
            flow_details (Dict[str, Any]): Dictionary containing flow class details.

        Returns:
            Dict[str, Any]: Dictionary containing the plan configuration.
        """
        flow_config = {
            "federated_flow": {
                "settings": {},
                "template": f"src.{self.script_name}.{flow_details['flow_class_name']}",
            }
        }

        def update_config_with_args(args: Dict[str, Any], arg_type: str = "args") -> None:
            """Update plan configuration with argument values.

            Args:
                args (Dict[str, Any]): Dictionary of arguments to process.
                arg_type (str): Type of arguments ('args' or 'kwargs').
            """
            for idx, (key, value) in enumerate(args.items()):
                if arg_type == "args":
                    # For positional args, get value from module or use as template reference
                    module_value = getattr(self.exported_script_module, str(key), None)
                    if module_value is not None and not isinstance(module_value, (int, str, bool)):
                        value = f"src.{self.script_name}.{key}"
                    else:
                        value = module_value
                    # Use expected arg name instead of variable name
                    key = flow_details["expected_args"][idx]
                elif arg_type == "kwargs":
                    # For keyword args, use template reference if not primitive type
                    if value is not None and not isinstance(value, (int, str, bool)):
                        value = f"src.{self.script_name}.{value}"

                flow_config["federated_flow"]["settings"].update({key: value})

        # Process positional and keyword arguments
        positional_args = flow_details["init_args"].get("args", {})
        update_config_with_args(positional_args, "args")

        keyword_args = flow_details["init_args"].get("kwargs", {})
        update_config_with_args(keyword_args, "kwargs")

        return flow_config
