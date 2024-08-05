# Copyright (C) 2020-2023 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""Federation API module."""

from typing import Dict, Union

from openfl.experimental.transport.grpc.director_client import DirectorClient
from openfl.utilities.utils import getfqdn_env


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
        tls: bool = True,
        client_id: str = None,
        # validate all certificates files are present
        # at given location
    ) -> None:
        self.director = director
        if self.director["director_node_fqdn"] is None:
            self.director_node_fqdn = getfqdn_env()
        else:
            self.director_node_fqdn = self.director["director_node_fqdn"]
        self.director_port = self.director["director_port"]
        self.tls = tls

        self.cert_chain = self.director["cert_chain"]
        self.api_cert = self.director["api_cert"]
        self.api_private_key = self.director["api_private_key"]

        self.envoy_details = envoys
        self.client_id = client_id

        # Create Director client
        self.dir_client = DirectorClient(
            director_host=self.director_node_fqdn,
            director_port=self.director_port,
            tls=self.tls,
            root_certificate=self.cert_chain,
            private_key=self.api_private_key,
            certificate=self.api_cert,
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

    def run_director(self) -> None:
        pass

    def run_envoys(self) -> None:
        pass

    def get_federation_info(self):
        """Returns federation details"""
        # TODO: Check what if director fails?
        #      What if someone calls this before starting director?

        envoys_info = self.dir_client.get_envoys_info()
        federation_info = {
            "director_info": {
                "director_node_fqdn": self.director_node_fqdn,
                "director_port": self.director_port,
            },
            "envoys": envoys_info,
        }

        return federation_info
