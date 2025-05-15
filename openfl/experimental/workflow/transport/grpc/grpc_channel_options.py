# Copyright 2020-2024 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

import time
from typing import Optional, Tuple

import grpc

max_metadata_size = 32 * 2**20
max_message_length = 2**30

channel_options = [
    ("grpc.max_metadata_size", max_metadata_size),
    ("grpc.max_send_message_length", max_message_length),
    ("grpc.max_receive_message_length", max_message_length),
]


class ConstantBackoff:
    """Constant Backoff policy."""

    def __init__(self, reconnect_interval, logger, uri, participant):
        """Initialize Constant Backoff."""
        self.reconnect_interval = reconnect_interval
        self.logger = logger
        self.uri = uri
        self.participant = participant

    def sleep(self):
        """Sleep for specified interval."""
        self.logger.info(f"Attempting to connect to {self.participant} at {self.uri}")
        time.sleep(self.reconnect_interval)


class RetryOnRpcErrorClientInterceptor(
    grpc.UnaryUnaryClientInterceptor, grpc.StreamUnaryClientInterceptor
):
    """Retry gRPC connection on failure."""

    def __init__(
        self,
        sleeping_policy,
        status_for_retry: Optional[Tuple[grpc.StatusCode]] = None,
    ):
        """Initialize function for gRPC retry."""
        self.sleeping_policy = sleeping_policy
        self.status_for_retry = status_for_retry

    def _intercept_call(self, continuation, client_call_details, request_or_iterator):
        """Intercept the call to the gRPC server."""
        while True:
            response = continuation(client_call_details, request_or_iterator)

            if isinstance(response, grpc.RpcError):
                # If status code is not in retryable status codes
                self.sleeping_policy.logger.info(f"Response code: {response.code()}")
                if self.status_for_retry and response.code() not in self.status_for_retry:
                    return response

                self.sleeping_policy.sleep()
            else:
                return response

    def intercept_unary_unary(self, continuation, client_call_details, request):
        """Wrap intercept call for unary->unary RPC."""
        return self._intercept_call(continuation, client_call_details, request)

    def intercept_stream_unary(self, continuation, client_call_details, request_iterator):
        """Wrap intercept call for stream->unary RPC."""
        return self._intercept_call(continuation, client_call_details, request_iterator)
