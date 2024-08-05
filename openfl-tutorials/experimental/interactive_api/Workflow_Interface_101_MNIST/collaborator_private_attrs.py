import torch
import torchvision

n_epochs = 3
batch_size_train = 64
batch_size_test = 1000
learning_rate = 0.01
momentum = 0.5
log_interval = 10

random_seed = 1
torch.backends.cudnn.enabled = False
torch.manual_seed(random_seed)

mnist_train = torchvision.datasets.MNIST(
    "./files/",
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
    "./files/",
    train=False,
    download=True,
    transform=torchvision.transforms.Compose(
        [
            torchvision.transforms.ToTensor(),
            torchvision.transforms.Normalize((0.1307,), (0.3081,)),
        ]
    ),
)


n_collaborators = 2
batch_size = 32

from copy import deepcopy

train = deepcopy(mnist_train)
test = deepcopy(mnist_test)

train.data = mnist_train.data[0::n_collaborators]
train.targets = mnist_train.targets[0::n_collaborators]
test.data = mnist_test.data[0::n_collaborators]
test.targets = mnist_test.targets[0::n_collaborators]

col1_private_attributes = {
    "train_loader": torch.utils.data.DataLoader(
        train, batch_size=batch_size, shuffle=True
    ),
    "test_loader": torch.utils.data.DataLoader(
        test, batch_size=batch_size, shuffle=True
    ),
}

train.data = mnist_train.data[1::n_collaborators]
train.targets = mnist_train.targets[1::n_collaborators]
test.data = mnist_test.data[1::n_collaborators]
test.targets = mnist_test.targets[1::n_collaborators]

col2_private_attributes = {
    "train_loader": torch.utils.data.DataLoader(
        train, batch_size=batch_size, shuffle=True
    ),
    "test_loader": torch.utils.data.DataLoader(
        test, batch_size=batch_size, shuffle=True
    ),
}
