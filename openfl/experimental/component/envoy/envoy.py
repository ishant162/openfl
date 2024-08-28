import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional, Type, Union

from openfl.experimental.federated import Plan
from openfl.experimental.interface.interactive_api.shard_descriptor import ShardDescriptor
from openfl.experimental.transport.grpc.director_client import DirectorClient

DEFAULT_RETRY_TIMEOUT_IN_SECONDS = 5


class Envoy:
    """Envoy class."""

    def __init__(
        self,
        *,
        envoy_name: str,
        director_host: str,
        director_port: int,
        shard_descriptor: Type[ShardDescriptor],
        root_certificate: Optional[Union[Path, str]] = None,
        private_key: Optional[Union[Path, str]] = None,
        certificate: Optional[Union[Path, str]] = None,
        tls: bool = True,
    ) -> None:
        """Initialize a envoy object."""
        self.name = envoy_name
        self.shard_descriptor = shard_descriptor
        self.root_certificate = (
            Path(root_certificate).absolute() if root_certificate is not None else None
        )
        self.private_key = Path(private_key).absolute() if root_certificate is not None else None
        self.certificate = Path(certificate).absolute() if root_certificate is not None else None
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

            # Experiment received
            # _run_collaborator

    # TODO: Think on how to implement this.
    #      What might be the health check about?
    def send_health_check(self):
        """Send health check to the director."""
        pass

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
            shard_descriptor=self.shard_descriptor,
        )
        col.run()

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
