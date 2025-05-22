# Copyright (C) 2020-2025 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

import logging
from openfl.experimental.workflow.interface import FLSpec
from openfl.experimental.workflow.placement import aggregator, collaborator
from tests.end_to_end.utils.wf_helper import get_test_attribute_sets

log = logging.getLogger(__name__)


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class TestFlowDynamicPrivateAttributeSync(FLSpec):
    """Test case to validate the dynamic assignment and synchronization of private attributes
    across aggregator and collaborators during Flow execution.
    """

    @aggregator
    def start(self):
        log.info(f"{bcolors.OKBLUE}Testing FederatedFlow - Starting Test {bcolors.ENDC}")
        self.collaborators = self.runtime.collaborators
        self.next(self.aggregator_step)

    @aggregator
    def aggregator_step(self):
        self.modify_private_attributes("agg")
        self.next(self.collaborator_step_b, foreach="collaborators")

    @collaborator
    def collaborator_step_b(self):
        self.modify_private_attributes(self.input)
        self.next(self.end)

    @aggregator
    def end(self, _):
        log.info(f"{bcolors.OKBLUE}Test round completed.{bcolors.ENDC}")

    def modify_private_attributes(self, participant) -> None:
        """Modify private attributes for the aggregator and collaborators."""
        test_attribute_sets = get_test_attribute_sets()
        for key, value in test_attribute_sets[participant].items():
            setattr(self, key, value)
