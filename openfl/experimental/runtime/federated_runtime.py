# Copyright (C) 2020-2023 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
""" openfl.experimental.runtime package LocalRuntime class."""

from __future__ import annotations

from typing import TYPE_CHECKING

from openfl.experimental.runtime.runtime import Runtime

if TYPE_CHECKING:
    from openfl.experimental.interface import Aggregator
    from openfl.experimental.interface import Collaborator
    from openfl.experimental.interface import Federation

from typing import List, Type, Dict, Any, Union


class ExperimentStatus:
    SUBMITTED = 0
    RUNNING = 1
    ERROR = 2
    FINISHED = 3

class FederatedRuntime(Runtime):

    def __init__(
        self,
        aggregator: str = None,
        collaborators: List[str] = None,
        federation: Type[Federation] = None,
        **kwargs,
    ) -> None:
        """
        Use single node to run the flow

        Args:
            aggregator:    Name of the aggregator.
            collaborators: List of collaborator names.
            federation:    Federation class object.

        Returns:
            None
        """
        super().__init__()
        self.aggregator = aggregator
        self.collaborators = collaborators
        # self.federation = federation

    @property
    def aggregator(self) -> str:
        """Returns name of _aggregator"""
        return self._aggregator

    @aggregator.setter
    def aggregator(self, aggregator: Type[Aggregator]):
        """Set LocalRuntime _aggregator"""
        self._aggregator = aggregator

    @property
    def collaborators(self) -> List[str]:
        """
        Return names of collaborators. Don't give direct access to private attributes
        """
        return self.__collaborators

    @collaborators.setter
    def collaborators(self, collaborators: List[Type[Collaborator]]):
        """Set LocalRuntime collaborators"""
        self.__collaborators = collaborators

    @property
    def federation(self) -> Type[Federation]:
        """Returns name of _aggregator"""
        return self.__federation

    @federation.setter
    def aggregator(self, federation: Type[Federation]):
        """Set LocalRuntime _aggregator"""
        self.__federation = federation

    def prepare_workspace_archive(self) -> None:
        # self.extract_private_attrs()
        self.__prepare_plan()
        self.__prepare_data()

    def extract_private_attrs(self) -> Dict[str, Any]:
        # This method will call workspace_export module and
        # extract private attributes from aggregator & collaborator.
        pass

    def __prepare_plan(
        self,
        arguments_required_to_initialize_the_flow,
        pickled_objects_name,
    ) -> None:
        # Prepare plan.yaml
        # Take plan template from openfl.experimental.interface.cli_helper.WORKSPACE "workspace/plan/plans/default/base_plan_interactive_api.yaml"
        # parse the plan
        # Fill the details for the new flow
        # 
        pass

    def __prepare_data(self) -> None:
        # Prepare data.yaml
        pass

    def remove_workspace_archive(self) -> None:
        # Delete experiment.zip file
        pass

    def submit_workspace(self) -> int:
        # Use federation._dir_client to submit workspace to Director
        return ExperimentStatus.SUBMITTED

    def stream_metrics(self) -> Dict[str, Union[str, float]]:
        # Use federation._dir_client object to get metrics and report to user
        pass

    def remove_experiment_data(self, flow_id: int) -> None:
        # Use federation._dir_client to remove experiment data including checkpoints
        pass

    def get_experiment_status(self) -> int:
        # Use federation._dir_client to comminicate to director to get experiment status
        # Return int as defined in ExperimentStatus
        return ExperimentStatus.SUBMITTED

    def __repr__(self):
        return "FederatedRuntime"
