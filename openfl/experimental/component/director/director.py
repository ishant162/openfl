# Copyright 2020-2024 Intel Corporation
# SPDX-License-Identifier: Apache-2.0


"""Director module."""
import asyncio
import time
from pathlib import Path
from typing import Callable, Union

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
        self._connected_envoys = {}

    # TODO: Need to Implement start_experiment_execution_loop properly
    async def start_experiment_execution_loop(self):
        """Run tasks and experiments here"""
        # In a infinite loop wait for experiment from experiment registry
        # Once the experiment received from registry
        # call experiment.start function

        # TODO: Implement this with Experiment registry context

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
                await run_aggregator_future

    # TODO: Need to Implement this
    async def wait_experiment(self, envoy_name: str) -> str:
        """Wait an experiment."""
        pass

    # TODO: Instead of passing arch_data, try to leverage existing functionality
    def set_new_experiment(self, arch_name, arch_data, experiment_name):
        """
        Save the archive at the current path
        """
        experiment = Experiment(
            name=experiment_name,
            archive_path=arch_name,
            archive_data=arch_data,
            collaborators=self.get_envoys(),
            plan_path="plan/plan.yaml",
        )

        self.experiments_registry.add(experiment)
        return True

    # TODO: first cut version might need improvement
    def acknowledge_envoys(self, envoy_name) -> bool:
        """
        Save the envoys
        """
        self._connected_envoys[envoy_name] = {
            "is_online": True,
            "is_experiment_running": False,
            "last_updated": time.time(),
        }
        return True

    # TODO: Add docstring, first cut version might need improvement
    def get_envoys(self):
        """
        Returns list of connected envoys
        """
        return list(self._connected_envoys.keys())
