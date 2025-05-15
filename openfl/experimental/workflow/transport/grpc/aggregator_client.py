# Copyright 2020-2025 Intel Corporation
# SPDX-License-Identifier: Apache-2.0


"""AggregatorGRPCClient module."""

from logging import getLogger

import grpc

from openfl.experimental.workflow.protocols import aggregator_pb2, aggregator_pb2_grpc
from openfl.experimental.workflow.transport.grpc.grpc_channel_options import (
    ConstantBackoff,
    RetryOnRpcErrorClientInterceptor,
    channel_options,
)
from openfl.protocols.utils import datastream_to_proto, proto_to_datastream


def _atomic_connection(func):
    def wrapper(self, *args, **kwargs):
        self.reconnect()
        response = func(self, *args, **kwargs)
        self.disconnect()
        return response

    return wrapper


def _resend_data_on_reconnection(func):
    def wrapper(self, *args, **kwargs):
        while True:
            try:
                response = func(self, *args, **kwargs)
            except grpc.RpcError as e:
                if e.code() == grpc.StatusCode.UNKNOWN:
                    self.logger.info(
                        f"Attempting to resend data request to aggregator at {self.uri}"
                    )
                elif e.code() == grpc.StatusCode.UNAUTHENTICATED:
                    raise
                continue
            break
        return response

    return wrapper


class AggregatorGRPCClient:
    """Client to the aggregator over gRPC-TLS."""

    def __init__(
        self,
        agg_addr,
        agg_port,
        disable_client_auth,
        root_certificate,
        certificate,
        private_key,
        tls=True,
        aggregator_uuid=None,
        federation_uuid=None,
        single_col_cert_common_name=None,
        **kwargs,
    ):
        """Initialize."""
        self.uri = f"{agg_addr}:{agg_port}"
        self.tls = tls
        self.disable_client_auth = disable_client_auth
        self.root_certificate = root_certificate
        self.certificate = certificate
        self.private_key = private_key

        self.logger = getLogger(__name__)

        if not self.tls:
            self.logger.warn("gRPC is running on insecure channel with TLS disabled.")
            self.channel = self.create_insecure_channel(self.uri)
        else:
            self.channel = self.create_tls_channel(
                self.uri,
                self.root_certificate,
                self.disable_client_auth,
                self.certificate,
                self.private_key,
            )

        self.header = None
        self.aggregator_uuid = aggregator_uuid
        self.federation_uuid = federation_uuid
        self.single_col_cert_common_name = single_col_cert_common_name

        # Adding an interceptor for RPC Errors
        self.interceptors = (
            RetryOnRpcErrorClientInterceptor(
                sleeping_policy=ConstantBackoff(
                    logger=self.logger,
                    reconnect_interval=int(kwargs.get("client_reconnect_interval", 1)),
                    uri=self.uri,
                    participant="Aggregator",
                ),
                status_for_retry=(grpc.StatusCode.UNAVAILABLE,),
            ),
        )
        self.stub = aggregator_pb2_grpc.AggregatorStub(
            grpc.intercept_channel(self.channel, *self.interceptors)
        )

    def create_insecure_channel(self, uri):
        """Set an insecure gRPC channel (i.e. no TLS) if desired.

        Warns user that this is not recommended.

        Args:
            uri: The uniform resource identifier of the insecure channel

        Returns:
            An insecure gRPC channel object
        """
        return grpc.insecure_channel(uri, options=channel_options)

    def create_tls_channel(
        self,
        uri,
        root_certificate,
        disable_client_auth,
        certificate,
        private_key,
    ):
        """Set an secure gRPC channel (i.e. TLS).

        Args:
            uri: The uniform resource identifier of the insecure channel
            root_certificate: The Certificate Authority filename
            disable_client_auth (boolean): True disabled client-side
             authentication (not recommended, throws warning to user)
            certificate: The client certificate filename from the collaborator
             (signed by the certificate authority)

        Returns:
            An insecure gRPC channel object
        """
        with open(root_certificate, "rb") as f:
            root_certificate_b = f.read()

        if disable_client_auth:
            self.logger.warn("Client-side authentication is disabled.")
            private_key_b = None
            certificate_b = None
        else:
            with open(private_key, "rb") as f:
                private_key_b = f.read()
            with open(certificate, "rb") as f:
                certificate_b = f.read()

        credentials = grpc.ssl_channel_credentials(
            root_certificates=root_certificate_b,
            private_key=private_key_b,
            certificate_chain=certificate_b,
        )

        return grpc.secure_channel(uri, credentials, options=channel_options)

    def _set_header(self, collaborator_name):
        self.header = aggregator_pb2.MessageHeader(
            sender=collaborator_name,
            receiver=self.aggregator_uuid,
            federation_uuid=self.federation_uuid,
            single_col_cert_common_name=self.single_col_cert_common_name or "",
        )

    def validate_response(self, reply, collaborator_name):
        """Validate the aggregator response."""
        assert reply.header.receiver == collaborator_name, (
            f"Receiver in response header does not match collaborator name. "
            f"Expected: {collaborator_name}, Actual: {reply.header.receiver}"
        )
        assert reply.header.sender == self.aggregator_uuid, (
            f"Sender in response header does not match aggregator UUID. "
            f"Expected: {self.aggregator_uuid}, Actual: {reply.header.sender}"
        )
        assert reply.header.federation_uuid == self.federation_uuid, (
            f"Federation UUID in response header does not match. "
            f"Expected: {self.federation_uuid}, Actual: {reply.header.federation_uuid}"
        )
        assert reply.header.single_col_cert_common_name == (
            self.single_col_cert_common_name or ""
        ), (
            f"Single collaborator certificate common name in response header does not match. "
            f"Expected: {self.single_col_cert_common_name or ''}, Actual: {reply.header.single_col_cert_common_name}"  # noqa: E501
        )

    def disconnect(self):
        """Close the gRPC channel."""
        self.logger.debug(f"Disconnecting from gRPC server at {self.uri}")
        self.channel.close()

    def reconnect(self):
        """Create a new channel with the gRPC server."""
        # channel.close() is idempotent. Call again here in case it wasn't
        # issued previously
        self.disconnect()

        if not self.tls:
            self.channel = self.create_insecure_channel(self.uri)
        else:
            self.channel = self.create_tls_channel(
                self.uri,
                self.root_certificate,
                self.disable_client_auth,
                self.certificate,
                self.private_key,
            )

        self.logger.debug(f"Connecting to gRPC at {self.uri}")

        self.stub = aggregator_pb2_grpc.AggregatorStub(
            grpc.intercept_channel(self.channel, *self.interceptors)
        )

    @_atomic_connection
    @_resend_data_on_reconnection
    def send_task_results(self, collaborator_name, round_number, next_step, clone_bytes):
        """Send next function name to aggregator."""
        self._set_header(collaborator_name)
        request = aggregator_pb2.TaskResultsRequest(
            header=self.header,
            collab_name=collaborator_name,
            round_number=round_number,
            next_step=next_step,
            execution_environment=clone_bytes,
        )

        response = self.stub.SendTaskResults(proto_to_datastream(request))
        self.validate_response(response, collaborator_name)

        return response.header

    @_atomic_connection
    @_resend_data_on_reconnection
    def get_tasks(self, collaborator_name):
        """Get tasks from the aggregator."""
        self._set_header(collaborator_name)
        request = aggregator_pb2.GetTasksRequest(header=self.header)
        response_stream = self.stub.GetTasks(request)
        response = datastream_to_proto(aggregator_pb2.GetTasksResponse(), response_stream)
        self.validate_response(response, collaborator_name)

        return (
            response.round_number,
            response.function_name,
            response.execution_environment,
            response.sleep_time,
            response.quit,
        )

    @_atomic_connection
    @_resend_data_on_reconnection
    def call_checkpoint(self, collaborator_name, clone_bytes, function, stream_buffer):
        """Perform checkpoint for collaborator task."""
        self._set_header(collaborator_name)

        request = aggregator_pb2.CheckpointRequest(
            header=self.header,
            execution_environment=clone_bytes,
            function=function,
            stream_buffer=stream_buffer,
        )

        response = self.stub.CallCheckpoint(proto_to_datastream(request))
        self.validate_response(response, collaborator_name)

        return response.header
