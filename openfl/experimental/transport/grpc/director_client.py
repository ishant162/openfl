
import logging
import grpc
from .grpc_channel_options import channel_options

from openfl.experimental.protocols import director_pb2
from openfl.experimental.protocols import director_pb2_grpc


class DirectorClient:
    """The director client class."""
    def __init__(
            self, *,
            director_host: str,
            director_port: int,
            envoy_name: str,
            tls: bool,
            root_certificate: str,
            private_key: str,
            certificate: str,
    ) -> None:
        """Initialize a director client object."""
        self.envoy_name = envoy_name
        director_addr = f'{director_host}:{director_port}'
        if not tls:
            channel = grpc.insecure_channel(director_addr, options=channel_options)
        else:
            if not (root_certificate and private_key and certificate):
                raise Exception('No certificates provided')
            try:
                with open(root_certificate, 'rb') as f:
                    root_certificate_b = f.read()
                with open(private_key, 'rb') as f:
                    private_key_b = f.read()
                with open(certificate, 'rb') as f:
                    certificate_b = f.read()
            except FileNotFoundError as exc:
                raise Exception(f'Provided certificate file is not exist: {exc.filename}')

            credentials = grpc.ssl_channel_credentials(
                root_certificates=root_certificate_b,
                private_key=private_key_b,
                certificate_chain=certificate_b
            )
            channel = grpc.secure_channel(director_addr, credentials, options=channel_options)
        self.stub = director_pb2_grpc.DirectorStub(channel)
        self.logger = logging.getLogger(__name__)

    def connect_envoy(self, envoy_name:str)-> bool:
        """Attempt to establish a connection to the director."""
        self.logger.info(f'Sending {envoy_name} connection request to director')

        request = director_pb2.SendConnectionRequest(envoy_name=envoy_name)
        response = self.stub.ConnectEnvoy(request)

        return response.accepted
    
    #TODO: Need to modify this rpc later to get_experiment_data()
    def wait_experiment(self):
        """Wait an experiment data from the director."""
        self.logger.info('Waiting for an experiment to run...')
        request = director_pb2.WaitExperimentRequest(
            collaborator_name=self.envoy_name
        )
        response = self.stub.WaitExperiment(request)
        # self.logger.info(f'New experiment received: {response}')
        experiment_name = response.experiment_name
        # if not experiment_name:
        #     raise Exception('No experiment')
        return experiment_name
    
    #TODO: Need to implement this
    def get_experiment_data(self, experiment_name):
        """Get an experiment data from the director."""
        pass