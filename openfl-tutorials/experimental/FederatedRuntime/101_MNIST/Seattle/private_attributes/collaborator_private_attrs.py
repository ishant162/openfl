# Copyright (C) 2020-2023 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

from copy import deepcopy

import torch
import torchvision

random_seed = 1
torch.backends.cudnn.enabled = False
torch.manual_seed(random_seed)
torch.use_deterministic_algorithms(True)

mnist_train = torchvision.datasets.MNIST(
    "../files/",
    train=True,
    download=True,
    transform=torchvision.transforms.Compose(
        [
            torchvision.transforms.ToTensor(),
            torchvision.transforms.Normalize((0.1307,), (0.3081,)),
        ]
    ),
)

mnist_test = torchvision.datasets.MNIST(
    "../files/",
    train=False,
    download=True,
    transform=torchvision.transforms.Compose(
        [
            torchvision.transforms.ToTensor(),
            torchvision.transforms.Normalize((0.1307,), (0.3081,)),
        ]
    ),
)


n_collaborators = 4
batch_size = 32

train = deepcopy(mnist_train)
test = deepcopy(mnist_test)

# train.data = mnist_train.data[1::n_collaborators]
# train.targets = mnist_train.targets[1::n_collaborators]
# test.data = mnist_test.data[1::n_collaborators]
# test.targets = mnist_test.targets[1::n_collaborators]

train.data = mnist_train.data[1:10000:n_collaborators]
train.targets = mnist_train.targets[1:10000:n_collaborators]
test.data = mnist_test.data[1:1000:n_collaborators]
test.targets = mnist_test.targets[1:1000:n_collaborators]

import random 
import numpy as np

def seed_worker(worker_id):
    # worker_seed = torch.initial_seed() % 2**32
    # np.random.seed(worker_seed)
    # random.seed(worker_seed)
    np.random.seed(0)
    random.seed(0)

g = torch.Generator()
g.manual_seed(0)

collaborator_private_attrs = {
    "train_loader": torch.utils.data.DataLoader(
        train, batch_size=batch_size, shuffle=False,num_workers=1, worker_init_fn=seed_worker,generator=g
    ),
    "test_loader": torch.utils.data.DataLoader(
        test, batch_size=batch_size, shuffle=False,num_workers=1, worker_init_fn=seed_worker,generator=g
    ),
}
