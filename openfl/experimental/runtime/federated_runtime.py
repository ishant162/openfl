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

from typing import List, Type


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

        Returns:
            None
        """
        super().__init__()
        self.aggregator = aggregator
        self.collaborators = collaborators
        self.federation = federation

    @property
    def aggregator(self) -> str:
        """Returns name of _aggregator"""
        return self._aggregator

    @aggregator.setter
    def aggregator(self, aggregator_name: Type[Aggregator]):
        """Set LocalRuntime _aggregator"""
        self._aggregator = aggregator_name

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
    def federation(self) -> str:
        """Returns name of _aggregator"""
        return self._federation

    @federation.setter
    def aggregator(self, federation: Type[Federation]):
        """Set LocalRuntime _aggregator"""
        self._federation = federation

    def start_services(self) -> None:
        # Will use federation object to start services.
        pass

    def populate_plan(self) -> None:
        pass

    def populate_data(self) -> None:
        pass

    def extract_private_attrs(self) -> dict:
        # This method will call workspace_export module and
        # extract private attributes from aggregator & collaborator.
        pass

    def __repr__(self):
        return "FederatedRuntime"
