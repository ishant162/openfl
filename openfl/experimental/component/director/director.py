# Copyright 2020-2024 Intel Corporation
# SPDX-License-Identifier: Apache-2.0


"""Director module."""
import asyncio
import logging
import pickle
import time
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Tuple, Union

from openfl.experimental.component.director.experiment import Experiment, ExperimentsRegistry
from openfl.experimental.transport.grpc.exceptions import EnvoyNotFoundError


class Director:
    """Director class."""

    def __init__(
        self,
        *,
        tls: bool = True,
        root_certificate: Union[Path, str] = None,
        private_key: Union[Path, str] = None,
        certificate: Union[Path, str] = None,
        director_config: Path = None,
        envoy_health_check_period: int = 60,
        install_requirements: bool = False,
    ) -> None:
        """Initialize a Director object.

        Args:
            tls (bool, optional): A flag indicating if TLS should be used for
                connections. Defaults to True.
            root_certificate (Union[Path, str], optional): The path to the
                root certificate for TLS. Defaults to None.
            private_key (Union[Path, str], optional): The path to the private
                key for TLS. Defaults to None.
            certificate (Union[Path, str], optional): The path to the
                certificate for TLS. Defaults to None.
            director_config (Path): Path to director_config file
            install_requirements (bool, optional): A flag indicating if the
                requirements should be installed. Defaults to False.
        """
        self.tls = tls
        self.root_certificate = root_certificate
        self.private_key = private_key
        self.certificate = certificate
        self.director_config = director_config
        self.install_requirements = install_requirements
        self._flow_status = []

        self.experiments_registry = ExperimentsRegistry()
        self.col_exp = {}
        self.col_exp_queues = defaultdict(asyncio.Queue)
        self._envoy_registry = {}
        self.envoy_health_check_period = envoy_health_check_period
        self.logger = logging.getLogger(__name__)

    async def start_experiment_execution_loop(self):
        """Run tasks and experiments here"""
        loop = asyncio.get_event_loop()
        while True:
            try:
                async with self.experiments_registry.get_next_experiment() as experiment:
                    run_aggregator_future = loop.create_task(
                        experiment.start(
                            root_certificate=self.root_certificate,
                            certificate=self.certificate,
                            private_key=self.private_key,
                            tls=self.tls,
                            director_config=self.director_config,
                            install_requirements=False,
                        )
                    )
                    # Adding the experiment to collaborators queues
                    for col_name in experiment.collaborators:
                        queue = self.col_exp_queues[col_name]
                        await queue.put(experiment.name)
                    # Wait for the experiment to complete and save the result
                    self._flow_status = await run_aggregator_future
            except Exception as e:
                raise Exception(f"Error while executing experiment: {e}")

    async def get_flow_status(self) -> Tuple[bool, bytes]:
        """Wait until the experiment is finished and return True.

        Returns:
            status (bool): The flow status.
            flspec_obj (bytes): A serialized FLSpec object (in bytes) using pickle.
        """
        while not self._flow_status:
            await asyncio.sleep(10)

        # Reset flow status
        status, flspec_obj = self._flow_status
        self._flow_status = []
        # Return flow_status when the status is FINISHED
        return status, pickle.dumps(flspec_obj)

    async def wait_experiment(self, envoy_name: str) -> str:
        """Wait an experiment.

        Args:
            envoy_name (str): The name of the envoy.

        Returns:
            str: The name of the experiment on the queue.
        """
        experiment_name = self.col_exp.get(envoy_name)
        # If any envoy gets disconnected
        if experiment_name and experiment_name in self.experiments_registry:
            experiment = self.experiments_registry[experiment_name]
            if experiment.aggregator.current_round < experiment.aggregator.rounds_to_train:
                return experiment_name

        self.col_exp[envoy_name] = None
        queue = self.col_exp_queues[envoy_name]
        experiment_name = await queue.get()
        self.col_exp[envoy_name] = experiment_name

        return experiment_name

    async def set_new_experiment(
        self,
        experiment_name: str,
        sender_name: str,
        collaborator_names: Iterable[str],
        experiment_archive_path: Path,
    ) -> bool:
        """Set new experiment.

        Args:
            experiment_name (str): String id for experiment.
            sender_name (str): The name of the sender.
            collaborator_names (Iterable[str]): Names of collaborators.
            experiment_archive_path (Path): Path of the experiment.

        Returns:
            bool : Boolean returned if the experiment register was successful.
        """
        experiment = Experiment(
            name=experiment_name,
            archive_path=experiment_archive_path,
            collaborators=collaborator_names,
            users=[sender_name],
            sender=sender_name,
            plan_path="plan/plan.yaml",
        )

        self.experiments_registry.add(experiment)
        return True

    def get_experiment_data(self, experiment_name: str) -> Path:
        """Get experiment data.

        Args:
            experiment_name (str): String id for experiment.

        Returns:
            str: Path of archive.
        """
        try:
            if experiment_name not in self.experiments_registry:
                raise KeyError(f"Experiment {experiment_name} not found in registry")
            return self.experiments_registry[experiment_name].archive_path
        except Exception as e:
            print(f"Error retrieving experiment data: {e}")
            return None

    def acknowledge_envoys(self, envoy_name: str) -> bool:
        """
        Save the envoys

        Args:
            envoy_name (str): Name of the envoy
        """
        self._envoy_registry[envoy_name] = {
            "is_online": True,
            "is_experiment_running": False,
            "last_updated": time.time(),
            "valid_duration": 2 * self.envoy_health_check_period,
        }
        return True

    def get_envoys(self):
        """Gets list of connected envoys

        Returns:
            envoys: list of connected envoys
        """
        envoys = list(self._envoy_registry.keys())
        return envoys

    def update_envoy_status(
        self,
        *,
        envoy_name: str,
        is_experiment_running: bool,
    ) -> int:
        """Accept health check from envoy.

        Args:
            envoy_name (str): String id for envoy.
            is_experiment_running (bool): Boolean value for the status of the
                experiment.

        Raises:
            EnvoyNotFoundError: When Unknown shard {envoy_name}.

        Returns:
            int: Value of the envoy_health_check_period.
        """
        shard_info = self._envoy_registry.get(envoy_name)
        if not shard_info:
            raise EnvoyNotFoundError(f"Unknown shard {envoy_name}")

        shard_info["is_online"]: True
        shard_info["is_experiment_running"] = is_experiment_running
        shard_info["valid_duration"] = 2 * self.envoy_health_check_period
        shard_info["last_updated"] = time.time()

        return self.envoy_health_check_period
