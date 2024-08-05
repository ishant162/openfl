# Copyright 2020-2024 Intel Corporation
# SPDX-License-Identifier: Apache-2.0


"""Python low-level API module."""
from typing import Dict, Type, Union

from openfl.transport.grpc.director_client import DirectorClient


class ExperimentStatus:
    SUBMITTED = 0
    RUNNING = 1
    ERROR = 2
    FINISHED = 3


class ExperimentManager:
    """Central class for experiment orchestration."""

    def __init__(
        self,
        dir_client: Type[DirectorClient],
    ) -> None:
        self.__dir_client = dir_client

    def get_experiment_status(self) -> int:
        # Use dir_client to comminicate to director to get experiment status
        # Return int as defined in ExperimentStatus
        return ExperimentStatus.SUBMITTED

    def stream_metrics(self) -> Dict[str, Union[str, float]]:
        # Use dir_client object to get metrics and report to user
        pass

    def remove_experiment_data(self, flow_id: int) -> None:
        # Remove experiment data including checkpoints
        pass

    def prepare_workspace_for_distribution(self) -> None:
        # Prepare 2 experiment.zip files, one for aggregator with file for
        # it's private attributes
        # And second zip for collaborators with it's private attributes
        self.__prepare_plan()
        self.__prepare_data()

    def remove_workspace_archive(self) -> None:
        # Delete experiment.zip file
        pass

    def __prepare_plan(self):
        # Prepare plan.yaml
        pass

    def __prepare_data(self):
        # Prepare data.yaml
        pass

    def submit_workspace(self):
        # Use dir_client to submit workspace to Director
        pass
