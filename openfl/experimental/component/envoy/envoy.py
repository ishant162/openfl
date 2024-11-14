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
    """Envoy class. The Envoy is a long-lived entity that runs on collaborator
    nodes connected to the Director.

    Attributes:
        envoy_name (str): The name of the envoy.
        root_certificate (Union[Path, str]): The path to the root certificate
            for TLS.
        private_key (Union[Path, str]): The path to the private key for TLS.
        certificate (Union[Path, str]): The path to the certificate for TLS.
        director_client (DirectorClient): The director client.
        install_requirements (bool): A flag indicating if the requirements
            should be installed.
        executor (ThreadPoolExecutor): The executor for running tasks.
        is_experiment_running (bool): A flag indicating if an experiment is
            running.
        plan(str): Path to plan.yaml
        _health_check_future (object): The future object for the health check.
    """

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
        """Initialize a envoy object.

        Args:
            envoy_name (str): The name of the envoy.
            director_host (str): The host of the director.
            director_port (int): The port of the director.
            envoy_config (Path): Path to envoy_config.yaml
            root_certificate (Optional[Union[Path, str]], optional): The path
                to the root certificate for TLS. Defaults to None.
            private_key (Optional[Union[Path, str]], optional): The path to
                the private key for TLS. Defaults to None.
            certificate (Optional[Union[Path, str]], optional): The path to
                the certificate for TLS. Defaults to None.
            tls (bool, optional): A flag indicating if TLS should be used for
                connections. Defaults to True.
            install_requirements (bool, optional): A flag indicating if the
                requirements should be installed. Defaults to True.
        """
        self.name = envoy_name
        self.envoy_config = envoy_config
        self.tls = tls
        self._fill_certs(root_certificate, private_key, certificate)
        self.install_requirements = install_requirements
        self.director_client = DirectorClient(
            director_host=director_host,
            director_port=director_port,
            envoy_name=envoy_name,
            tls=self.tls,
            root_certificate=self.root_certificate,
            private_key=self.private_key,
            certificate=self.certificate,
        )
        self.logger = logging.getLogger(__name__)
        self.is_experiment_running = False
        self.executor = ThreadPoolExecutor()
        self.plan = "plan/plan.yaml"

    def _fill_certs(self, root_certificate, private_key, certificate):
        """Fill certificates.

        Args:
            root_certificate (Union[Path, str]): The path to the root
                certificate for the TLS connection.
            private_key (Union[Path, str]): The path to the server's private
                key for the TLS connection.
            certificate (Union[Path, str]): The path to the server's
                certificate for the TLS connection.
        """
        if self.tls:
            if not (root_certificate and private_key and certificate):
                raise Exception("No certificates provided")
            self.root_certificate = Path(root_certificate).absolute()
            self.private_key = Path(private_key).absolute()
            self.certificate = Path(certificate).absolute()
        else:
            self.root_certificate = self.private_key = self.certificate = None

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
                    # TODO: Implement review_plan_callback
                    self.is_experiment_running = True
                    self._run_collaborator()
            except Exception as exc:
                self.logger.exception("Collaborator failed with error: %s:", exc)
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
                if response.size == len(response.exp_data):
                    data_file.write(response.exp_data)
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
                    "The director has lost information about current envoy. Resending..."
                )
                self.director_client.connect_envoy(envoy_name=self.name)
            time.sleep(timeout)

    def _run_collaborator(self) -> None:
        """Run the collaborator for the experiment running."""
        plan = Plan.parse(plan_config_path=Path(self.plan))
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
                self.logger.info(f"{self.name} is connected to the director")
                self._health_check_future = self.executor.submit(self.send_health_check)
                self.run()
            else:
                # Connection failed
                self.logger.error(f"{self.name} failed to connect to the director")
                sys.exit(1)
