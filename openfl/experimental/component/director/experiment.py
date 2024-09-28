# Copyright 2020-2024 Intel Corporation
# SPDX-License-Identifier: Apache-2.0


"""Experiment module."""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Callable, List, Union

from openfl.experimental.federated import Plan
from openfl.experimental.transport import AggregatorGRPCServer
from openfl.experimental.utilities.workspace import ExperimentWorkspace

logger = logging.getLogger(__name__)


class Status:
    """Experiment's statuses."""

    PENDING = "pending"
    FINISHED = "finished"
    IN_PROGRESS = "in_progress"
    FAILED = "failed"
    REJECTED = "rejected"


class Experiment:
    """Experiment class."""

    def __init__(
        self,
        *,
        name: str,
        archive_path: Union[Path, str],
        archive_data,
        collaborators: List[str],
        plan_path: Union[Path, str] = "plan/plan.yaml",
    ) -> None:
        """Initialize an experiment object."""
        self.name = name
        self.archive_path = Path(archive_path).absolute()
        self.archive_data = archive_data
        self.collaborators = collaborators
        self.plan_path = Path(plan_path)
        self.status = Status.PENDING
        self.aggregator = None
        self.run_aggregator_atask = None

    async def start(
        self,
        *,
        tls: bool = True,
        root_certificate: Union[Path, str] = None,
        private_key: Union[Path, str] = None,
        certificate: Union[Path, str] = None,
        director_config: dict = None,
        install_requirements: bool = False,
    ):
        """Run experiment."""
        self.status = Status.IN_PROGRESS
        try:
            logger.info(f"New experiment {self.name} for " f"collaborators {self.collaborators}")

            # TODO: To be implemented with ExperimentWorkspace context
            with ExperimentWorkspace(
                experiment_name=self.name,
                data_file_path=self.archive_path,
                arch_data=self.archive_data,
                install_requirements=install_requirements,
            ):
                aggregator_grpc_server = self._create_aggregator_grpc_server(
                    tls=tls,
                    root_certificate=root_certificate,
                    private_key=private_key,
                    certificate=certificate,
                    director_config=director_config,
                )
                self.aggregator = aggregator_grpc_server.aggregator
                await asyncio.gather(
                    self._run_aggregator_grpc_server(
                        aggregator_grpc_server=aggregator_grpc_server,
                    ),
                    self.aggregator.run_experiment(),
                )
            self.status = Status.FINISHED
            logger.info("Experiment %s was finished successfully.", self.name)
        except Exception as e:
            self.status = Status.FAILED
            logger.exception("Experiment %s failed with error: %s.", self.name, e)

    async def review_experiment(self, review_plan_callback: Callable) -> bool:
        """Get plan approve in console."""
        logger.debug("Experiment Review starts")
        # Extract the workspace for review (without installing requirements)
        with ExperimentWorkspace(
            self.name,
            self.archive_path,
            is_install_requirements=False,
            remove_archive=False,
        ):
            loop = asyncio.get_event_loop()
            # Call for a review in a separate thread (server is not blocked)
            review_approve = await loop.run_in_executor(
                None, review_plan_callback, self.name, self.plan_path
            )
            if not review_approve:
                self.status = Status.REJECTED
                self.archive_path.unlink(missing_ok=True)
                return False

        logger.debug("Experiment Review succeeded")
        return True

    def _create_aggregator_grpc_server(
        self,
        *,
        tls: bool = True,
        root_certificate: Union[Path, str] = None,
        private_key: Union[Path, str] = None,
        certificate: Union[Path, str] = None,
        director_config: dict = None,
    ) -> AggregatorGRPCServer:
        plan = Plan.parse(plan_config_path=self.plan_path)
        plan.authorized_cols = list(self.collaborators)

        logger.info("🧿 Created an Aggregator Server for %s experiment.", self.name)
        aggregator_grpc_server = plan.get_server(
            root_certificate=root_certificate,
            certificate=certificate,
            private_key=private_key,
            tls=tls,
            director_config=director_config,
        )
        return aggregator_grpc_server

    @staticmethod
    async def _run_aggregator_grpc_server(
        aggregator_grpc_server: AggregatorGRPCServer,
    ) -> None:
        """Run aggregator."""
        logger.info("🧿 Starting the Aggregator Service.")
        grpc_server = aggregator_grpc_server.get_server()
        grpc_server.start()
        logger.info("Starting Aggregator gRPC Server")

        # try:
        #     while not aggregator_grpc_server.aggregator.all_quit_jobs_sent():
        #         # Awaiting quit job sent to collaborators
        #         await asyncio.sleep(10)
        #     logger.debug("Aggregator sent quit jobs calls to all collaborators")
        # except KeyboardInterrupt:
        #     pass
        # finally:
        # pass
        # grpc_server.stop(0)


class ExperimentsRegistry:
    """ExperimentsList class."""

    def __init__(self) -> None:
        """Initialize an experiments list object."""
        self.__active_experiment_name = None
        self.__pending_experiments = []
        self.__archived_experiments = []
        self.__dict = {}

    @property
    def active_experiment(self) -> Union[Experiment, None]:
        """Get active experiment."""
        if self.__active_experiment_name is None:
            return None
        return self.__dict[self.__active_experiment_name]

    @property
    def pending_experiments(self) -> List[str]:
        """Get queue of not started experiments."""
        return self.__pending_experiments

    def add(self, experiment: Experiment) -> None:
        """Add experiment to queue of not started experiments."""
        self.__dict[experiment.name] = experiment
        self.__pending_experiments.append(experiment.name)

    def remove(self, name: str) -> None:
        """Remove experiment from everywhere."""
        if self.__active_experiment_name == name:
            self.__active_experiment_name = None
        if name in self.__pending_experiments:
            self.__pending_experiments.remove(name)
        if name in self.__archived_experiments:
            self.__archived_experiments.remove(name)
        if name in self.__dict:
            del self.__dict[name]

    def __getitem__(self, key: str) -> Experiment:
        """Get experiment by name."""
        return self.__dict[key]

    def get(self, key: str, default=None) -> Experiment:
        """Get experiment by name."""
        return self.__dict.get(key, default)

    def get_user_experiments(self, user: str) -> List[Experiment]:
        """Get list of experiments for specific user."""
        return [exp for exp in self.__dict.values() if user in exp.users]

    def __contains__(self, key: str) -> bool:
        """Check if experiment exists."""
        return key in self.__dict

    def finish_active(self) -> None:
        """Finish active experiment."""
        self.__archived_experiments.insert(0, self.__active_experiment_name)
        self.__active_experiment_name = None

    @asynccontextmanager
    async def get_next_experiment(self):
        """Context manager.

        On enter get experiment from pending_experiments.
        On exit put finished experiment to archive_experiments.
        """
        while True:
            if self.active_experiment is None and self.pending_experiments:
                break
            await asyncio.sleep(10)

        try:
            self.__active_experiment_name = self.pending_experiments.pop(0)
            yield self.active_experiment
        finally:
            self.finish_active()
