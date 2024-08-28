# Copyright (C) 2020-2023 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""Envoy CLI."""

import logging
import shutil
import sys
from importlib import import_module
from pathlib import Path

import click
from click import Path as ClickPath
from click import group, option, pass_context
from dynaconf import Validator

from openfl.experimental.interface.cli.cli_helper import WORKSPACE
from openfl.utilities import click_types, merge_configs
from openfl.utilities.path_check import is_directory_traversal

logger = logging.getLogger(__name__)


@group()
@pass_context
def envoy(context):
    """Manage Federated Learning Envoy."""
    context.obj["group"] = "envoy"


@envoy.command(name="start")
@option("-n", "--envoy_name", required=True, help="Current shard name")
@option(
    "-dh",
    "--director-host",
    required=True,
    help="The FQDN of the federation director",
    type=click_types.FQDN,
)
@option(
    "-dp",
    "--director-port",
    required=True,
    help="The federation director port",
    type=click.IntRange(1, 65535),
)
@option(
    "--tls/--disable-tls",
    default=True,
    is_flag=True,
    help="Use TLS or not (By default TLS is enabled)",
)
@option(
    "-ec",
    "--envoy-config-path",
    default="envoy_config.yaml",
    help="The envoy config path",
    type=ClickPath(exists=True),
)
@option(
    "-rc",
    "--root-cert-path",
    "root_certificate",
    default=None,
    help="Path to a root CA cert",
    type=ClickPath(exists=True),
)
@option(
    "-pk",
    "--private-key-path",
    "private_key",
    default=None,
    help="Path to a private key",
    type=ClickPath(exists=True),
)
@option(
    "-oc",
    "--public-cert-path",
    "certificate",
    default=None,
    help="Path to a signed certificate",
    type=ClickPath(exists=True),
)
def start_(
    envoy_name,
    director_host,
    director_port,
    tls,
    envoy_config_path,
    root_certificate,
    private_key,
    certificate,
):
    """Start the Envoy."""

    from openfl.experimental.component.envoy import Envoy

    logger.info("🧿 Starting the Envoy.")
    if is_directory_traversal(envoy_config_path):
        click.echo("The envoy config path is out of the openfl workspace scope.")
        sys.exit(1)

    config = merge_configs(
        settings_files=envoy_config_path,
        overwrite_dict={
            "root_certificate": root_certificate,
            "private_key": private_key,
            "certificate": certificate,
        },
        validators=[
            Validator("params.cuda_devices", default=[]),
            Validator("params.install_requirements", default=True),
            Validator("params.review_experiment", default=False),
        ],
    )

    if config.root_certificate:
        config.root_certificate = Path(config.root_certificate).absolute()
    if config.private_key:
        config.private_key = Path(config.private_key).absolute()
    if config.certificate:
        config.certificate = Path(config.certificate).absolute()

    # Instantiate Shard Descriptor
    shard_descriptor = shard_descriptor_from_config(config.get("shard_descriptor", {}))

    envoy = Envoy(
        envoy_name=envoy_name,
        director_host=director_host,
        director_port=director_port,
        shard_descriptor=shard_descriptor,
        tls=tls,
        root_certificate=config.root_certificate,
        private_key=config.private_key,
        certificate=config.certificate,
    )

    envoy.start()


@envoy.command(name="create-workspace")
@option("-p", "--envoy-path", required=True, help="The Envoy path", type=ClickPath())
def create(envoy_path):
    """Create an envoy workspace."""
    if is_directory_traversal(envoy_path):
        click.echo("The Envoy path is out of the openfl workspace scope.")
        sys.exit(1)
    envoy_path = Path(envoy_path).absolute()
    if envoy_path.exists():
        if not click.confirm("Envoy workspace already exists. Recreate?", default=True):
            sys.exit(1)
        shutil.rmtree(envoy_path)
    (envoy_path / "cert").mkdir(parents=True, exist_ok=True)
    (envoy_path / "logs").mkdir(parents=True, exist_ok=True)
    (envoy_path / "data").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(
        WORKSPACE / "default/envoy_config.yaml",
        envoy_path / "envoy_config.yaml",
    )
    shutil.copyfile(WORKSPACE / "default/requirements.txt", envoy_path / "requirements.txt")


def shard_descriptor_from_config(shard_config: dict):
    """Build a shard descriptor from config."""
    template = shard_config.get("template")
    if not template:
        raise Exception("You should define a shard " "descriptor template in the envoy config")
    class_name = template.split(".")[-1]
    module_path = ".".join(template.split(".")[:-1])
    params = shard_config.get("settings", {})

    module = import_module(module_path)
    instance = getattr(module, class_name)(**params)

    return instance
