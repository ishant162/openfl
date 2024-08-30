# Copyright (C) 2020-2023 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

from openfl.experimental.interface import FLSpec
from openfl.experimental.placement import aggregator, collaborator

import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import torch
import numpy as np

# MNIST parameters
learning_rate = 5e-2
momentum = 5e-1
log_interval = 20

# Watermarking parameters
watermark_pretrain_learning_rate = 1e-1
watermark_pretrain_momentum = 5e-1
watermark_pretrain_weight_decay = 5e-05
watermark_retrain_learning_rate = 5e-3


def inference(network, test_loader):
    network.eval()
    correct = 0
    with torch.no_grad():
        for data, target in test_loader:
            output = network(data)
            pred = output.data.max(1, keepdim=True)[1]
            correct += pred.eq(target.data.view_as(pred)).sum()
    accuracy = float(correct / len(test_loader.dataset))
    return accuracy


def train_model(model, optimizer, data_loader, entity, round_number, log=False):
    # Helper function to train the model
    train_loss = 0
    model.train()
    for batch_idx, (X, y) in enumerate(data_loader):
        optimizer.zero_grad()

        output = model(X)
        loss = F.nll_loss(output, y)
        loss.backward()

        optimizer.step()

        train_loss += loss.item() * len(X)
        if batch_idx % log_interval == 0 and log:
            print(f"{entity:<20} Train Epoch: {round_number:<3}"
                  + f" [{batch_idx * len(X):<3}/{len(data_loader.dataset):<4}"
                  + f" ({100.0 * batch_idx / len(data_loader):<.0f}%)]"
                  + f" Loss: {loss.item():<.6f}")
    train_loss /= len(data_loader.dataset)
    return train_loss


def fedavg(agg_model, models):
    state_dicts = [model.state_dict() for model in models]
    state_dict = agg_model.state_dict()
    for key in models[0].state_dict():
        state_dict[key] = np.sum(
            np.array([state[key] for state in state_dicts], dtype=object),
            axis=0) / len(models)
    agg_model.load_state_dict(state_dict)
    return agg_model


class Net(nn.Module):
    def __init__(self, dropout=0.0):
        super(Net, self).__init__()
        self.dropout = dropout
        self.block = nn.Sequential(
            nn.Conv2d(1, 32, 2),
            nn.MaxPool2d(2),
            nn.ReLU(),
            nn.Conv2d(32, 64, 2),
            nn.MaxPool2d(2),
            nn.ReLU(),
            nn.Conv2d(64, 128, 2),
            nn.ReLU(),
        )
        self.fc1 = nn.Linear(128 * 5**2, 200)
        self.fc2 = nn.Linear(200, 10)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(p=dropout)

    def forward(self, x):
        x = self.dropout(x)
        out = self.block(x)
        out = out.view(-1, 128 * 5**2)
        out = self.dropout(out)
        out = self.relu(self.fc1(out))
        out = self.dropout(out)
        out = self.fc2(out)
        return F.log_softmax(out, 1)


class FederatedFlow_MNIST_Watermarking(FLSpec):  # NOQA N801
    """
    This Flow demonstrates Watermarking on a Deep Learning Model in Federated Learning
    Ref: WAFFLE: Watermarking in Federated Learning (https://arxiv.org/abs/2008.07298)
    """

    def __init__(
        self,
        model=None,
        optimizer=None,
        watermark_pretrain_optimizer=None,
        watermark_retrain_optimizer=None,
        round_number=0,
        n_rounds=4,
        **kwargs,
    ):
        super().__init__(**kwargs)

        if model is not None:
            self.model = model
            self.optimizer = optimizer
            self.watermark_pretrain_optimizer = watermark_pretrain_optimizer
            self.watermark_retrain_optimizer = watermark_retrain_optimizer
        else:
            self.model = Net()
            self.optimizer = optim.SGD(
                self.model.parameters(), lr=learning_rate, momentum=momentum
            )
            self.watermark_pretrain_optimizer = optim.SGD(
                self.model.parameters(),
                lr=watermark_pretrain_learning_rate,
                momentum=watermark_pretrain_momentum,
                weight_decay=watermark_pretrain_weight_decay,
            )
            self.watermark_retrain_optimizer = optim.SGD(
                self.model.parameters(), lr=watermark_retrain_learning_rate
            )
        self.round_number = round_number
        self.n_rounds = n_rounds

    @aggregator
    def start(self):
        """
        This is the start of the Flow.
        """
        print("<Agg>: Start of flow ... ")
        self.collaborators = self.runtime.collaborators
        self.next(self.watermark_pretrain)

    @aggregator
    def watermark_pretrain(self):
        """
        Pre-Train the Model before starting Federated Learning.
        """
        print(f"<Agg>: watermark_pretrain")
        self.next(
            self.aggregated_model_validation,
            foreach="collaborators",
        )

    @collaborator
    def aggregated_model_validation(self):
        """
        Perform Aggregated Model validation on Collaborators.
        """
        print(f"<Collab>: Aggregated Model validation")

        self.next(self.train)

    @collaborator
    def train(self):
        """
        Train model on Local collab dataset.
        """
        print("<Collab>: Performing Model Training on Local dataset ... ")
        print(f'train_loader: {self.train_loader}')
        print(f'train_loader: {self.test_loader}')
        self.next(self.local_model_validation)

    @collaborator
    def local_model_validation(self):
        """
        Validate locally trained model.
        """
        print(
            f"<Collab> Local model validation"
        )
        self.next(self.join)

    @aggregator
    def join(self, inputs):
        """
        Model aggregation step.
        """
        print("<Agg>: Join ... ")
        self.next(self.watermark_retrain)

    @aggregator
    def watermark_retrain(self):
        """
        Retrain the aggregated model.
        """
        print("<Agg>: Performing Watermark Retraining ... ")
        self.next(self.end)

    @aggregator
    def end(self):
        """
        This is the last step in the Flow.
        """
        print("This is the end of the flow")
