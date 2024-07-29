# Copyright (C) 2020-2023 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""Federation API module."""

from openfl.transport.grpc.director_client import DirectorClient
from openfl.utilities.utils import getfqdn_env
from .shard_descriptor import DummyShardDescriptor


class Federation:
    """
    Federation class.

    Federation entity exists to keep information about collaborator related settings,
    their local data and network setting to enable communication in federation.
    """

    def __init__(
        self,
        director_fqdn: str,
        director_port: int,
        director_user: str,
        director_password: str,
        director_identity_file: str,
        tls: bool,
        envoy_details: dict,
    ) -> None:
        self.director_fqdn = director_fqdn
        self.director_port = director_port
        self.__director_user = director_user
        self.__director_password = director_password
        self.director_identity_file = director_identity_file
        self.__tls = tls
        self.envoy_details = envoy_details

    @property
    def director_fqdn(self) -> str:
        return self.__director_fqdn

    @director_fqdn.setter
    def director_fqdn(self, director_fqdn: str):
        # validate FQDN
        self.__director_fqdn = director_fqdn

    @property
    def director_port(self) -> int:
        return self.__director_port

    @director_port.setter
    def director_port(self, director_port: int):
        # validate that assigned port is in between 0 to 65353 range
        self.__director_port = director_port

    @property
    def director_identity_file(self) -> str:
        return self.__director_identity_file

    @director_identity_file.setter
    def director_identity_file(self, director_identity_file: str):
        # validate that the file exists on given location
        self.__director_identity_file = director_identity_file

    @property
    def envoy_details(self) -> dict:
        return self.__envoy_details

    @envoy_details.setter
    def envoy_details(self, envoy_details: dict):
        # validate dict make all required information is provided and
        # validate each envoy FQDN
        # validate envoy port
        # identity file
        self.__envoy_details = envoy_details

    def run_director(self) -> None:
        pass

    def run_envoys(self) -> None:
        pass
