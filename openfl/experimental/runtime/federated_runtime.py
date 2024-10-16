# Copyright 2020-2024 Intel Corporation
# SPDX-License-Identifier: Apache-2.0


""" openfl.experimental.runtime package LocalRuntime class."""

from __future__ import annotations

import logging
import os
import pickle
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from openfl.experimental.runtime.runtime import Runtime
from openfl.experimental.transport.grpc.director_client import DirectorClient

if TYPE_CHECKING:
    from openfl.experimental.interface import Aggregator
    from openfl.experimental.interface import Collaborator

from typing import Dict, List, Type, Union


class ExperimentStatus:
    SUBMITTED = 0
    RUNNING = 1
    ERROR = 2
    FINISHED = 3


# TODO: Update Docstring and Arguments description
class FederatedRuntime(Runtime):
    """Class for a federated runtime, derived from the Runtime class.

    Attributes:
        aggregator (Type[Aggregator]): The aggregator participant.
        collaborators (List[Type[Collaborator]]): The list of collaborator
            participants.
    """

    def __init__(
        self,
        aggregator: str = None,
        collaborators: List[str] = None,
        director: Dict = None,
        notebook_path: str = None,
        tls: bool = False,
        **kwargs,
    ) -> None:
        """Initializes the FederatedRuntime object.

        Use single node to run the flow.

        Args:
            aggregator (str, optional): Name of the aggregator. Defaults to
                None.
            collaborators (List[str], optional): List of collaborator names.
                Defaults to None.
            director (Dict): Director information. Defaults to None
            **kwargs: Additional keyword arguments.
        """
        super().__init__()
        if aggregator is not None:
            self.aggregator = aggregator

        if collaborators is not None:
            self.collaborators = collaborators

        self.notebook_path = notebook_path
        self.tls = tls

        if director:
            self.director = director
            self._fill_certs(
                self.director["cert_chain"],
                self.director["api_private_key"],
                self.director["api_cert"],
            )

            self._dir_client = DirectorClient(
                director_host=self.director["director_node_fqdn"],
                director_port=self.director["director_port"],
                tls=tls,
                root_certificate=self.root_certificate,
                private_key=self.private_key,
                certificate=self.certificate,
            )

        self.kwargs = kwargs
        self.generated_workspace_path = None
        self.logger = logging.getLogger(__name__)

    @property
    def aggregator(self) -> str:
        """Returns name of _aggregator."""
        return self._aggregator

    @aggregator.setter
    def aggregator(self, aggregator_name: Type[Aggregator]):
        """Set LocalRuntime _aggregator.

        Args:
            aggregator_name (Type[Aggregator]): The name of the aggregator to
                set.
        """
        self._aggregator = aggregator_name

    @property
    def collaborators(self) -> List[str]:
        """Return names of collaborators.

        Don't give direct access to private attributes.

        Returns:
            List[str]: The names of the collaborators.
        """
        return self.__collaborators

    @collaborators.setter
    def collaborators(self, collaborators: List[Type[Collaborator]]):
        """Set LocalRuntime collaborators.

        Args:
            collaborators (List[Type[Collaborator]]): The list of
                collaborators to set.
        """
        self.__collaborators = collaborators

    def _fill_certs(self, root_certificate, private_key, certificate):
        """Fill certificates."""
        if self.tls:
            if not all([root_certificate, private_key, certificate]):
                raise ValueError("No certificates provided")

            self.root_certificate = Path(root_certificate).absolute()
            self.private_key = Path(private_key).absolute()
            self.certificate = Path(certificate).absolute()
        else:
            self.root_certificate = self.private_key = self.certificate = None

    def prepare_workspace_archive(self) -> None:
        """
        Prepare workspace archive using WorkspaceExport

        Returns:
            archive_path: Path of the archive created.
        """
        from openfl.experimental.workspace_export import WorkspaceExport

        self.generated_workspace_path, archive_path, exp_name = WorkspaceExport.export(
            notebook_path=self.notebook_path,
            output_workspace="./generated_workspace",
            federated_runtime=True,
        )

        return archive_path, exp_name

    def remove_workspace_archive(self, archive_path) -> None:
        """
        Removes workspace archive
        """
        os.remove(archive_path)

    def submit_workspace(self, archive_path, exp_name) -> int:
        """
        Submits workspace archive to the director
        """
        try:
            response = self._dir_client.set_new_experiment(
                archive_path=archive_path, experiment_name=exp_name, col_names=self.get_envoys()
            )
        finally:
            self.remove_workspace_archive(archive_path)

        return response

    def stream_metrics(self) -> Dict[str, Union[str, float]]:
        # Use _dir_client object to get metrics and report to user
        pass

    def remove_experiment_data(self, flow_id: int) -> None:
        # Use _dir_client to remove experiment data including checkpoints
        pass

    def get_flow_status(self) -> int:

        status, flspec_obj = self._dir_client.get_flow_status()
        sys.path.append(str(self.generated_workspace_path))
        return status, pickle.loads(flspec_obj)

    def get_envoys(self):
        """Gets Envoys

        Returns:
            list: A list of envoys.
        """
        envoys = self._dir_client.get_envoys()
        return envoys

    def __repr__(self):
        return "FederatedRuntime"
