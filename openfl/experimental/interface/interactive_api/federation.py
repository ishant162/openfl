# Copyright (C) 2020-2023 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""Federation API module."""

from typing import Dict, Union

from openfl.transport.grpc.director_client import DirectorClient


class Federation:
    """
    Federation class.

    Federation entity exists to keep information about collaborator related settings,
    their local data and network setting to enable communication in federation.
    """

    def __init__(
        self,
        director: Dict[str, Union[str, int]],
        envoys: Dict[str, Union[str, int]],
        tls: bool,
        client_id: str = None,
        cert_chain: str = None,
        api_cert: str = None,
        api_private_key: str = None,
    ) -> None:
        self.director = director
        self.envoy_details = envoys
        self._dir_client = DirectorClient(
            client_id=client_id,
            director_host=self.director["fqdn"],
            director_port=self.director["port"],
            tls=tls,
            # validate all certificates files are present
            # at given location
            root_certificate=cert_chain,
            private_key=api_private_key,
            certificate=api_cert,
        )

    @property
    def director(self) -> Dict[str, Union[str, int]]:
        return self.__director

    @director.setter
    def director(self, director: Dict[str, Union[str, int]]):
        # validate dict make sure all required information is provided as following:
        # 1. FQDN, port, username, password OR identity file and,
        # validate envoy FQDN using regex
        # make sure director port provided is within valid range 0 to 65535
        # make sure identity file if provided then is located at given path
        self.__director = director

    @property
    def envoy_details(self) -> Dict[str, Union[str, int]]:
        return self.__envoy_details

    @envoy_details.setter
    def envoy_details(self, envoy_details: Dict[str, Union[str, int]]):
        # validate dict make sure all required information is provided as following:
        # 1. FQDN, port, username, password OR identity file and,
        # validate envoy FQDN using regex
        # make sure envoy port provided is within valid range 0 to 65535
        # make sure identity file if provided then is located at given path
        self.__envoy_details = envoy_details