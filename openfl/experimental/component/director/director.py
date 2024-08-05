import logging
from pathlib import Path
from typing import Callable, Union


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
        install_requirements: bool = False,
    ) -> None:
        """Initialize a director object."""
        self.envoys_connected = {}
        self.tls = tls
        self.root_certificate = root_certificate
        self.private_key = private_key
        self.certificate = certificate
        # self.experiments_registry = ExperimentsRegistry()
        # self.col_exp_queues = defaultdict(asyncio.Queue)
        # self.col_exp = {}
        self.review_plan_callback = review_plan_callback
        self.envoy_health_check_period = envoy_health_check_period
        self.install_requirements = install_requirements

        self.logger = logging.getLogger(__name__)

    # TODO: Need to Implement this
    async def start_experiment_execution_loop(self):
        """Run tasks and experiments here"""
        pass

    # TODO: Need to Implement this
    async def wait_experiment(self, envoy_name: str) -> str:
        """Wait an experiment."""
        pass

    def acknowledge_envoy(self, envoy_name):
        """Save envoy info to envoys_connected"""
        self.logger.info(f"{envoy_name} is connected to the Director")
        self.envoys_connected[envoy_name] = {
            "envoy_name": envoy_name,
            "is_online": True,
        }
        is_accepted = True
        return is_accepted

    def get_envoys(self):
        return self.envoys_connected
