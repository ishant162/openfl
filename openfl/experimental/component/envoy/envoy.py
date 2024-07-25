import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Optional, Type, Union

from openfl.experimental.transport.grpc.director_client import DirectorClient
from openfl.plugins.processing_units_monitor.cuda_device_monitor import (
    CUDADeviceMonitor,
)

DEFAULT_RETRY_TIMEOUT_IN_SECONDS = 5


class Envoy:
    """Envoy class."""

    def __init__(
        self,
        *,
        envoy_name: str,
        director_host: str,
        director_port: int,
        root_certificate: Optional[Union[Path, str]] = None,
        private_key: Optional[Union[Path, str]] = None,
        certificate: Optional[Union[Path, str]] = None,
        tls: bool = True,
        install_requirements: bool = True,
        cuda_devices: Union[tuple, list] = (),
        cuda_device_monitor: Optional[Type[CUDADeviceMonitor]] = None,
        review_plan_callback: Union[None, Callable] = None,
    ) -> None:
        """Initialize a envoy object."""
        self.name = envoy_name
        self.root_certificate = (
            Path(root_certificate).absolute()
            if root_certificate is not None
            else None
        )
        self.private_key = (
            Path(private_key).absolute()
            if root_certificate is not None
            else None
        )
        self.certificate = (
            Path(certificate).absolute()
            if root_certificate is not None
            else None
        )
        self.director_client = DirectorClient(
            director_host=director_host,
            director_port=director_port,
            envoy_name=envoy_name,
            tls=tls,
            root_certificate=root_certificate,
            private_key=private_key,
            certificate=certificate,
        )
        self.logger = logging.getLogger(__name__)
        self.cuda_devices = tuple(cuda_devices)
        self.install_requirements = install_requirements

        self.review_plan_callback = review_plan_callback

        # Optional plugins
        self.cuda_device_monitor = cuda_device_monitor

        self.executor = ThreadPoolExecutor()
        self.running_experiments = {}
        self.is_experiment_running = False
        self._health_check_future = None

    # TODO: Need to implement self.director_client.get_experiment_data()
    #      after experiment design
    def run(self):
        """Run of the envoy working cycle."""
        while True:
            try:
                # Get experiment name
                experiment_name = self.director_client.wait_experiment()
                if not experiment_name:
                    time.sleep(1000)
            except Exception as exc:
                self.logger.exception(f"Failed to get experiment: {exc}")
                time.sleep(DEFAULT_RETRY_TIMEOUT_IN_SECONDS)
                continue

            # TODO: Need to proceed with received experiment

    # TODO: Think on how to implement this.
    #      What might be the health check about?
    def send_health_check(self):
        """Send health check to the director."""
        pass

    # TODO: Get more info on this and its implementation
    def _get_cuda_device_info(self):
        pass

    # TODO: To be implemented after experiment design
    def _run_collaborator(self, plan="plan/plan.yaml"):
        """Run the collaborator for the experiment running."""
        pass

    def start(self):
        """Start the envoy."""
        is_accepted = self.director_client.connect_envoy(envoy_name=self.name)
        if is_accepted:
            self.logger.info(f"{self.name} was connected to the director")
            # TODO: Submit send_health_check to self.executor
            self.run()
        else:
            # Connection failed
            self.logger.error(f"{self.name} failed to connect to the director")
            sys.exit(1)
