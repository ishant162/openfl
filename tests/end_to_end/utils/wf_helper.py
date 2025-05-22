# Copyright 2020-2023 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

from metaflow import Flow
import logging
import torch
from torch.utils.data import DataLoader
import torchvision
import datetime
import numpy as np
from typing import Dict, Any

log = logging.getLogger(__name__)


def validate_flow(flow_obj, expected_flow_steps):
    """
    Validate:
    1. If the given training round were completed
    2. If all the steps were executed
    3. If each collaborator step was executed
    4. If end was executed once
    """

    cli_flow_obj = Flow("TestFlowInternalLoop")  # Flow object from CLI
    cli_flow_steps = list(cli_flow_obj.latest_run)  # Steps from CLI
    cli_step_names = [step.id for step in cli_flow_steps]

    # 1. If the given training round were completed
    assert flow_obj.training_rounds == flow_obj.train_count, "Number of training completed is not equal to training rounds"

    for step in cli_flow_steps:
        task_count = 0
        func = getattr(flow_obj, step.id)
        for task in list(step):
            task_count = task_count + 1

        # Each aggregator step should be executed for training rounds times
        if (
            (func.aggregator_step is True)
            and (task_count != flow_obj.training_rounds)
            and (step.id != "end")
        ):
            assert False, f"More than one execution detected for Aggregator Step: {step}"

        # Each collaborator step is executed for (training rounds)*(number of collaborator) times
        if (func.collaborator_step is True) and (
            task_count != len(flow_obj.collaborators) * flow_obj.training_rounds
        ):
            assert False, f"Incorrect number of execution detected for Collaborator Step: {step}. Expected: {flow_obj.training_rounds*len(flow_obj.collaborators)} Actual: {task_count}"

    steps_present_in_cli = [
        step for step in expected_flow_steps if step in cli_step_names
    ]
    missing_steps_in_cli = [
        step for step in expected_flow_steps if step not in cli_step_names
    ]
    extra_steps_in_cli = [
        step for step in cli_step_names if step not in expected_flow_steps
    ]
    return steps_present_in_cli, missing_steps_in_cli, extra_steps_in_cli


def get_test_attribute_sets() -> Dict[str, Dict[str, Any]]:
    """
    Generates a test dictionary of private attributes for multiple entities, including various
    data types.

    Returns:
        Dict[str, Dict[str, Any]]: A dictionary where each key is an entity name
        (e.g., 'Aggregator', 'Paris') and the value is another dictionary of mock
        private attributes using a variety of data types.
    """
    torch.backends.cudnn.enabled = False
    torch.manual_seed(1)

    transform = torchvision.transforms.Compose(
        [torchvision.transforms.ToTensor(), torchvision.transforms.Normalize((0.1307,), (0.3081,))]
    )

    train_loader = DataLoader(
        torchvision.datasets.MNIST("files/", train=True, download=True, transform=transform),
        batch_size=128,
        shuffle=True,
    )

    test_loader = DataLoader(
        torchvision.datasets.MNIST("files/", train=False, download=True, transform=transform),
        batch_size=128,
        shuffle=True,
    )

    return {
        "agg": {
            "private_attribute_1": train_loader,
            "private_attribute_2": test_loader,
            "private_attribute_3": 3.14,
            "private_attribute_4": np.array([1, 2, 3]),
        },
        "collaborator0": {
            "private_attribute_1": True,
            "private_attribute_2": [1, 2, 3],
            "private_attribute_3": {"a": 1},
            "private_attribute_4": None,
        },
        "collaborator1": {
            "private_attribute_1": (4, 5),
            "private_attribute_2": b"bytes",
            "private_attribute_3": complex(1, 2),
            "private_attribute_4": np.int64(10),
        },
        "collaborator2": {
            "private_attribute_1": {1, 2, 3},
            "private_attribute_2": frozenset([4, 5]),
            "private_attribute_3": range(5),
            "private_attribute_4": np.float32(5.5),
        },
        "collaborator3": {
            "private_attribute_1": bytearray(b"abc"),
            "private_attribute_2": memoryview(b"xyz"),
            "private_attribute_3": slice(1, 5, 2),
            "private_attribute_4": np.bool_(False),
        },
        "collaborator4": {
            "private_attribute_1": NotImplemented,
            "private_attribute_2": Ellipsis,
            "private_attribute_3": memoryview(bytearray(b"test")),
            "private_attribute_4": np.complex64(3 + 4j),
        },
        "collaborator5": {
            "private_attribute_1": set(),
            "private_attribute_2": type,
            "private_attribute_3": super,
            "private_attribute_4": datetime.datetime(2023, 1, 1),
        },
    }


def dataloader_equal(dl1, dl2):
    """Check if two DataLoader objects are equal.
    Args:
        dl1 (torch.utils.data.DataLoader): First DataLoader object.
        dl2 (torch.utils.data.DataLoader): Second DataLoader object.
    """
    return (
        isinstance(dl1, torch.utils.data.DataLoader)
        and isinstance(dl2, torch.utils.data.DataLoader)
        and dl1.batch_size == dl2.batch_size
        and type(dl1.dataset) is type(dl2.dataset)
        and isinstance(dl1.sampler, type(dl2.sampler))
    )

def check_modified_private_attributes(participant, expected_attributes) -> None:
    """Check if the participant's private_attributes match the expected values.
    Args:
        participant (Participant): The participant (aggregator or collaborator) to check.
        expected_attributes (dict): The expected private attributes.
    """
    actual_attributes = participant.private_attributes
    mismatches = []

    for key, expected_value in expected_attributes.items():
        actual_value = actual_attributes.get(key, "<Missing>")
        if isinstance(expected_value, np.ndarray) and isinstance(actual_value, np.ndarray):
            equal = np.array_equal(actual_value, expected_value)
        elif isinstance(expected_value, torch.utils.data.DataLoader):
            equal = dataloader_equal(actual_value, expected_value)
        else:
            equal = actual_value == expected_value

        if not equal:
            mismatches.append((key, actual_value, expected_value))

    if mismatches:
        print(f"{participant.name} attribute mismatches detected:")
        for key, actual, expected in mismatches:
            print(f"- {key}: actual={actual} | expected={expected}")
        raise AssertionError(f"{len(mismatches)} mismatches found in {participant.name}")
    else:
        print(
            f"{participant.name} attributes "
            f"match expected values!"
        )


def init_collaborator_private_attr_index(param):
        """
        Initialize a collaborator's private attribute index.

        Args:
            param (int): The initial value for the index.

        Returns:
            dict: A dictionary with the key 'index' and the value of `param` incremented by 1.
        """
        return {"index": param + 1}


def init_collaborator_private_attr_name(param):
        """
        Initialize a collaborator's private attribute name.

        Args:
            param (str): The name to be assigned to the collaborator's private attribute.

        Returns:
            dict: A dictionary with the key 'name' and the value of the provided parameter.
        """
        return {"name": param}


def init_collaborate_pvt_attr_np(param):
    """
    Initialize private attributes for collaboration with numpy arrays.

    This function generates random numpy arrays for training and testing loaders
    based on the given parameter.

    Args:
        param (int): A multiplier to determine the size of the generated arrays.

    Returns:
        dict: A dictionary containing:
            - "train_loader" (numpy.ndarray): A numpy array of shape (param * 50, 28, 28) with random values.
            - "test_loader" (numpy.ndarray): A numpy array of shape (param * 10, 28, 28) with random values.
    """
    return {
        "train_loader": np.random.rand(param * 50, 28, 28),
        "test_loader": np.random.rand(param * 10, 28, 28),
    }


def init_agg_pvt_attr_np():
    """
    Initialize a dictionary with a private attribute for testing.

    Returns:
        dict: A dictionary containing a single key "test_loader" with a value
              of a NumPy array of shape (10, 28, 28) filled with random values.
    """
    return {"test_loader": np.random.rand(10, 28, 28)}


def init_mock_pvt_attr(**kwargs):
    """
    Initialize a dictionary with private attributes for testing.

    Returns:
        dict: A dictionary containing four keys "private_attribute_1", "private_attribute_2",
              "private_attribute_3", and "private_attribute_4", each with a value of a NumPy
              array of shape (10, 28, 28) filled with random values.
    """
    return {f"private_attribute_{i}": np.random.rand(10, 28, 28) for i in range(1, 5)}
