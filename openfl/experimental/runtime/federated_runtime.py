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
    from openfl.experimental.interface import ExperimentManager
    from openfl.experimental.interface import ExperimentStatus

from typing import List, Type, Dict, Any


class FederatedRuntime(Runtime):

    def __init__(
        self,
        aggregator: str,
        collaborators: List[str],
        federation: Type[Federation],
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
        self.federation = federation
        self.__experiment_mgr = ExperimentManager(self.federation._dir_client)

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

    def start_director(self) -> None:
        # Use federation object to start service.
        self.federation.run_director()

    def start_envoys(self) -> None:
        # Use federation object to start service.
        self.federation.run_envoys()

    def prepare_workspace_archive(self) -> None:
        self.__experiment_mgr.prepare_workspace_for_distribution()

    def extract_private_attrs(self) -> Dict[str, Any]:
        # This method will call workspace_export module and
        # extract private attributes from aggregator & collaborator.
        pass

    def submit_workspace(self) -> bool:
        # Submit workspace to director
        return self.__experiment_mgr.submit_workspace()

    def stream_metrics(self) -> Dict[str, float]:
        # Get metrics from aggregator to director to here to experiment mgr
        # to user.
        return self.__experiment_mgr.stream_metrics()

    def experiment_status(self) -> int:
        # Get experiment status from director and send to experiment mgr.
        return self.__experiment_mgr.get_experiment_status()

    def __repr__(self):
        return "FederatedRuntime"
