# Copyright 2020-2024 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

import logging
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional, Union

from openfl.experimental.federated import Plan
from openfl.experimental.transport.grpc.director_client import DirectorClient
from openfl.experimental.transport.grpc.exceptions import EnvoyNotFoundError
from openfl.utilities.workspace import ExperimentWorkspace

DEFAULT_RETRY_TIMEOUT_IN_SECONDS = 5


class Envoy:
    """Envoy class."""

    def __init__(
        self,
        *,
        envoy_name: str,
        director_host: str,
        director_port: int,
        envoy_config: Path = None,
        root_certificate: Optional[Union[Path, str]] = None,
        private_key: Optional[Union[Path, str]] = None,
        certificate: Optional[Union[Path, str]] = None,
        tls: bool = True,
        install_requirements: bool = False,
    ) -> None:
        """Initialize a envoy object."""
        self.name = envoy_name
        self.envoy_config = envoy_config
        self.root_certificate = (
            Path(root_certificate).absolute() if root_certificate is not None else None
        )
        self.private_key = Path(private_key).absolute() if root_certificate is not None else None
        self.certificate = Path(certificate).absolute() if root_certificate is not None else None
        self.tls = tls
        self.install_requirements = install_requirements
        self.director_client = DirectorClient(
            director_host=director_host,
            director_port=director_port,
            envoy_name=envoy_name,
            tls=self.tls,
            root_certificate=root_certificate,
            private_key=private_key,
            certificate=certificate,
        )
        self.logger = logging.getLogger(__name__)
        self.is_experiment_running = False
        self.executor = ThreadPoolExecutor()

    def run(self):
        """Run of the envoy working cycle."""
        while True:
            try:
                # Wait for experiment
                experiment_name = self.director_client.wait_experiment()
                data_stream = self.director_client.get_experiment_data(experiment_name)
            except Exception as exc:
                self.logger.exception("Failed to get experiment: %s", exc)
                time.sleep(DEFAULT_RETRY_TIMEOUT_IN_SECONDS)
                continue
            data_file_path = self._save_data_stream_to_file(data_stream)

            try:
                with ExperimentWorkspace(
                    experiment_name=f"{self.name}_{experiment_name}",
                    data_file_path=data_file_path,
                    install_requirements=self.install_requirements,
                ):
                    self.is_experiment_running = True
                    self._run_collaborator()
            except Exception as exc:
                self.logger.exception("Collaborator failed with error: %s:", exc)
                # TODO: Implement set_experiment_failed functionality
            finally:
                self.is_experiment_running = False

    @staticmethod
    def _save_data_stream_to_file(data_stream):
        """Save data stream to file.

        Args:
            data_stream: The data stream to save.

        Returns:
            Path: The path to the saved data file.
        """
        data_file_path = Path(str(uuid.uuid4())).absolute()
        with open(data_file_path, "wb") as data_file:
            for response in data_stream:
                if response.size == len(response.npbytes):
                    data_file.write(response.npbytes)
                else:
                    raise Exception("Broken archive")
        return data_file_path

    def send_health_check(self):
        """Send health check to the director."""
        self.logger.debug("Sending envoy node status to director.")
        timeout = DEFAULT_RETRY_TIMEOUT_IN_SECONDS
        while True:
            try:
                timeout = self.director_client.send_health_check(
                    envoy_name=self.name,
                    is_experiment_running=self.is_experiment_running,
                )
            except EnvoyNotFoundError:
                self.logger.info(
                    "The director has lost information about current shard. Resending..."
                )
                self.director_client.connect_envoy(envoy_name=self.name)
            time.sleep(timeout)

    def _run_collaborator(self, plan="plan/plan.yaml"):
        """
        Run the collaborator for the experiment running.

        Args:
            plan: plan.yaml file path

        Returns:
            None
        """
        plan = Plan.parse(plan_config_path=Path(plan))
        self.logger.info("🧿 Starting the Collaborator Service.")

        col = plan.get_collaborator(
            self.name,
            self.root_certificate,
            self.private_key,
            self.certificate,
            envoy_config=self.envoy_config,
            tls=self.tls,
        )
        col.run()

    def start(self):
        """Start the envoy"""
        try:
            is_accepted = self.director_client.connect_envoy(envoy_name=self.name)
        except Exception as exc:
            self.logger.exception("Failed to connect envoy: %s", exc)
            sys.exit(1)
        else:
            if is_accepted:
                self.logger.info(f"{self.name} was connected to the director")
                self._health_check_future = self.executor.submit(self.send_health_check)
                self.run()
            else:
                # Connection failed
                self.logger.error(f"{self.name} failed to connect to the director")
                sys.exit(1)
