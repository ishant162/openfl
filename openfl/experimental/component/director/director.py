# Copyright 2020-2024 Intel Corporation
# SPDX-License-Identifier: Apache-2.0


"""Director module."""

import asyncio
from pathlib import Path
from typing import Callable, Union

from openfl.experimental.component.director.experiment import Experiment


class Director:
    """Director class."""

    def __init__(
        self,
        *,
        tls: bool = True,
        root_certificate: Union[Path, str] = None,
        private_key: Union[Path, str] = None,
        certificate: Union[Path, str] = None,
        review_plan_callback: Union[None, Callable] = None,
        envoy_health_check_period: int = 60,
        install_requirements: bool = False
    ) -> None:
        """Initialize a director object."""
        self.tls = tls
        self.root_certificate = root_certificate
        self.private_key = private_key
        self.certificate = certificate
        self.review_plan_callback = review_plan_callback
        self.envoy_health_check_period = envoy_health_check_period
        self.install_requirements = install_requirements

    # TODO: Need to Implement start_experiment_execution_loop properly
    async def start_experiment_execution_loop(self):
        """Run tasks and experiments here"""
        # In a infinite loop wait for experiment from experiment registry
        # Once the experiment received from registry
        # call experiment.start function

        # TODO: Implement this with Experiment registry context

        await asyncio.sleep(5)
        experiment = Experiment(
            name="FederatedFlow_MNIST_Watermarking",
            archive_path="",
            collaborators=[],
            sender="",
            init_tensor_dict={},
            plan_path="plan/plan.yaml",
        )

        await experiment.start(
            root_certificate=self.root_certificate,
            certificate=self.certificate,
            private_key=self.private_key,
            tls=self.tls,
            install_requirements=self.install_requirements,
        )

    # TODO: Need to Implement this
    async def wait_experiment(self, envoy_name: str) -> str:
        """Wait an experiment."""
        pass
