import logging

import grpc

from openfl.experimental.protocols import director_pb2, director_pb2_grpc

from .grpc_channel_options import channel_options


class DirectorClient:
    """The director client class."""

    def __init__(
        self,
        *,
        director_host: str,
        director_port: int,
        envoy_name: str = None,
        tls: bool,
        root_certificate: str,
        private_key: str,
        certificate: str,
    ) -> None:
        """Initialize a director client object."""
        self.envoy_name = envoy_name
        director_addr = f"{director_host}:{director_port}"
        if not tls:
            channel = grpc.insecure_channel(director_addr, options=channel_options)
        else:
            if not (root_certificate and private_key and certificate):
                raise Exception("No certificates provided")
            try:
                with open(root_certificate, "rb") as f:
                    root_certificate_b = f.read()
                with open(private_key, "rb") as f:
                    private_key_b = f.read()
                with open(certificate, "rb") as f:
                    certificate_b = f.read()
            except FileNotFoundError as exc:
                raise Exception(f"Provided certificate file is not exist: {exc.filename}")

            credentials = grpc.ssl_channel_credentials(
                root_certificates=root_certificate_b,
                private_key=private_key_b,
                certificate_chain=certificate_b,
            )
            channel = grpc.secure_channel(director_addr, credentials, options=channel_options)
        self.stub = director_pb2_grpc.DirectorStub(channel)
        self.logger = logging.getLogger(__name__)

    def connect_envoy(self, envoy_name: str) -> bool:
        """Attempt to establish a connection with the director."""
        self.logger.info(f"Sending {envoy_name} connection request to director")

        request = director_pb2.SendConnectionRequest(envoy_name=envoy_name)
        response = self.stub.ConnectEnvoy(request)

        return response.accepted

    def wait_experiment(self):
        """
        Wait an experiment data from the director.

        Returns:
            experiment_name (str): The name of the experiment.
        """
        self.logger.info("Waiting for an experiment to run...")
        response = self.stub.WaitExperiment(self._get_experiment_data())
        self.logger.info("New experiment received: %s", response)
        experiment_name = response.experiment_name
        if not experiment_name:
            raise Exception("No experiment")

        return experiment_name

    def get_experiment_data(self, experiment_name):
        """
        Get an experiment data from the director.

        Args:
            experiment_name (str): The name of the experiment.

        Returns:
            data_stream (grpc._channel._MultiThreadedRendezvous): The data
                stream of the experiment data.
        """
        self.logger.info("Getting experiment data for %s...", experiment_name)
        request = director_pb2.GetExperimentDataRequest(
            experiment_name=experiment_name, collaborator_name=self.envoy_name
        )
        data_stream = self.stub.GetExperimentData(request)

        return data_stream

    def _get_experiment_data(self):
        """Generate the experiment data request.

        Returns:
            director_pb2.WaitExperimentRequest: The request for experiment
                data.
        """
        return director_pb2.WaitExperimentRequest(collaborator_name=self.envoy_name)

    def set_new_experiment(self, archive_path, experiment_name, col_names):
        """
        Send the new experiment to director to launch.

        Args:
            experiment_name (str): The name of the experiment.
            col_names (List[str]): The names of the collaborators.
            archive_path (str): The path to the architecture.

        Returns:
            resp (director_pb2.SetNewExperimentResponse): The response from
                the director.
        """
        self.logger.info("Submitting new experiment %s to director", experiment_name)

        experiment_info_gen = self._get_experiment_info(
            arch_path=archive_path,
            name=experiment_name,
            col_names=col_names,
        )
        resp = self.stub.SetNewExperiment(experiment_info_gen)
        return resp

    def _get_experiment_info(self, arch_path, name, col_names):
        """
        Generate the experiment data request.

        This method generates a stream of experiment data to be sent to the
        director.

        Args:
            arch_path (str): The path to the architecture.
            name (str): The name of the experiment.
            col_names (List[str]): The names of the collaborators.

        Yields:
            director_pb2.ExperimentInfo: The experiment data.
        """
        with open(arch_path, "rb") as arch:
            max_buffer_size = 2 * 1024 * 1024
            chunk = arch.read(max_buffer_size)
            while chunk != b"":
                if not chunk:
                    raise StopIteration
                experiment_info = director_pb2.ExperimentInfo(
                    name=name,
                    collaborator_names=col_names,
                )
                experiment_info.experiment_data.size = len(chunk)
                experiment_info.experiment_data.npbytes = chunk
                yield experiment_info
                chunk = arch.read(max_buffer_size)

    def get_envoys(self):
        """Get envoys info.

        Returns:
            envoys = List of envoys
        """
        envoys = self.stub.GetEnvoys(director_pb2.GetEnvoysRequest())
        return envoys.columns

    def get_flow_status(self):
        """
        Gets status of the flow

        Returns:
            status = flow status
        """
        response = self.stub.GetFlowStatus(director_pb2.GetFlowStatusRequest())

        return response.completed, response.flspec_obj
