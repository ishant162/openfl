# Copyright 2020-2024 Intel Corporation
# SPDX-License-Identifier: Apache-2.0


"""Director module."""
import asyncio
import time
from collections import defaultdict
from pathlib import Path
from typing import Callable, Iterable, Union

from openfl.experimental.component.director.experiment import Experiment, ExperimentsRegistry


class Director:
    """Director class."""

    def __init__(
        self,
        *,
        tls: bool = True,
        root_certificate: Union[Path, str] = None,
        private_key: Union[Path, str] = None,
        certificate: Union[Path, str] = None,
        director_config: dict = None,
        review_plan_callback: Union[None, Callable] = None,
        envoy_health_check_period: int = 60,
        install_requirements: bool = False,
    ) -> None:
        """Initialize a director object."""
        self.tls = tls
        self.root_certificate = root_certificate
        self.private_key = private_key
        self.certificate = certificate
        self.director_config = director_config
        self.review_plan_callback = review_plan_callback
        self.envoy_health_check_period = envoy_health_check_period
        self.install_requirements = install_requirements

        self.experiments_registry = ExperimentsRegistry()
        self.col_exp = {}
        self.col_exp_queues = defaultdict(asyncio.Queue)
        self._connected_envoys = {}

    async def start_experiment_execution_loop(self):
        """Run tasks and experiments here"""

        loop = asyncio.get_event_loop()
        while True:
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
                await run_aggregator_future

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

    # TODO: Look what's use of sender and user in current implementation
    async def set_new_experiment(
        self,
        experiment_name: str,
        collaborator_names: Iterable[str],
        experiment_archive_path: Path,
    ) -> bool:
        """Set new experiment.

        Args:
            experiment_name (str): String id for experiment.
            collaborator_names (Iterable[str]): Names of collaborators.
            experiment_archive_path (Path): Path of the experiment.

        Returns:
            bool : Boolean returned if the experiment register was successful.
        """
        experiment = Experiment(
            name=experiment_name,
            archive_path=experiment_archive_path,
            collaborators=collaborator_names,
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
        return self.experiments_registry[experiment_name].archive_path

    # TODO: first cut version might need improvement
    def acknowledge_envoys(self, envoy_name: str) -> bool:
        """
        Save the envoys

        Args:
            envoy_name (str): Name of the envoy
        """
        self._connected_envoys[envoy_name] = {
            "is_online": True,
            "is_experiment_running": False,
            "last_updated": time.time(),
        }
        return True

    # TODO: Add docstring, first cut version might need improvement
    def get_envoys(self):
        """Returns list of connected envoys"""
        return list(self._connected_envoys.keys())
