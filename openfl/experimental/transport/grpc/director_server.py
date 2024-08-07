import asyncio
import logging
from pathlib import Path
from typing import Callable, Optional, Union

from grpc import aio, ssl_server_credentials

from openfl.experimental.protocols import director_pb2, director_pb2_grpc

from .grpc_channel_options import channel_options


class DirectorGRPCServer(director_pb2_grpc.DirectorServicer):
    """Director transport class."""

    def __init__(
        self,
        *,
        director_cls,
        tls: bool = True,
        root_certificate: Optional[Union[Path, str]] = None,
        private_key: Optional[Union[Path, str]] = None,
        certificate: Optional[Union[Path, str]] = None,
        review_plan_callback: Union[None, Callable] = None,
        listen_host: str = "[::]",
        listen_port: int = 50051,
        envoy_health_check_period: int = 0,
        **kwargs,
    ) -> None:
        super().__init__()
        self.listen_uri = f"{listen_host}:{listen_port}"
        self.tls = tls
        self.root_certificate = None
        self.private_key = None
        self.certificate = None
        self._fill_certs(root_certificate, private_key, certificate)
        self.server = None
        self.root_dir = Path.cwd()
        self.director = director_cls(
            tls=self.tls,
            root_certificate=self.root_certificate,
            private_key=self.private_key,
            certificate=self.certificate,
            review_plan_callback=review_plan_callback,
            envoy_health_check_period=envoy_health_check_period,
            **kwargs,
        )
        self.logger = logging.getLogger(__name__)

    def _fill_certs(self, root_certificate, private_key, certificate):
        """Fill certificates."""
        if self.tls:
            if not (root_certificate and private_key and certificate):
                raise Exception("No certificates provided")
            self.root_certificate = Path(root_certificate).absolute()
            self.private_key = Path(private_key).absolute()
            self.certificate = Path(certificate).absolute()

    def start(self):
        """Launch the director GRPC server."""
        loop = asyncio.get_event_loop()
        loop.create_task(self.director.start_experiment_execution_loop())
        loop.run_until_complete(self._run_server())

    async def _run_server(self):
        self.server = aio.server(options=channel_options)
        director_pb2_grpc.add_DirectorServicer_to_server(self, self.server)

        if not self.tls:
            self.server.add_insecure_port(self.listen_uri)
        else:
            with open(self.private_key, "rb") as f:
                private_key_b = f.read()
            with open(self.certificate, "rb") as f:
                certificate_b = f.read()
            with open(self.root_certificate, "rb") as f:
                root_certificate_b = f.read()
            server_credentials = ssl_server_credentials(
                ((private_key_b, certificate_b),),
                root_certificates=root_certificate_b,
                require_client_auth=True,
            )
            self.server.add_secure_port(self.listen_uri, server_credentials)
        self.logger.info(f"Starting director server on {self.listen_uri}")
        await self.server.start()
        await self.server.wait_for_termination()

    def ConnectEnvoy(self, request, context):
        self.logger.info(f"{request.envoy_name} is attempting to connect")
        self.logger.info(f"{request.envoy_name} is connected")
        accepted = True
        return director_pb2.RequestAccepted(accepted=accepted)

    # TODO: Need to Implement self.director.wait_experiment()
    async def WaitExperiment(self, request, context):
        """Request for wait an experiment."""
        self.logger.debug(
            f"Request WaitExperiment received from envoy {request.collaborator_name}"
        )
        experiment_name = await self.director.wait_experiment(
            request.collaborator_name
        )
        self.logger.debug(
            f"Experiment {experiment_name} is ready for {request.collaborator_name}"
        )

        return director_pb2.WaitExperimentResponse(
            experiment_name=experiment_name
        )
