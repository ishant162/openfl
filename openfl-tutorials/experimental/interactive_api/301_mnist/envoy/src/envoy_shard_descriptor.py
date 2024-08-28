import torch
from copy import deepcopy
from openfl.experimental.interface.interactive_api import ShardDescriptor


class EnvoyShardDescriptor(ShardDescriptor):
    """Shard descriptor class."""

    def __init__(self, **kwargs):
        self.shard_num = kwargs['shard_num']
        self.n_collaborators = kwargs['n_collaborators']
        self.batch_size = kwargs['batch_size']

    def download_data(self):
        """
        Download Watermark MNIST dataset
        """
        from .envoy_data import train_dataset, test_dataset

        return train_dataset, test_dataset

    def get_dataset(self):
        """
        Returns train and test dataset.
        """
        train_dataset, test_dataset = self.download_data()
        return train_dataset, test_dataset
    
    def get_private_attributes(self):
        """
        Return private attributes in the dict format
        """
        train_dataset, test_dataset = self.get_dataset()
        train = deepcopy(train_dataset)
        test = deepcopy(test_dataset)
        train.data = train_dataset.data[self.shard_num::self.n_collaborators]
        train.targets = train_dataset.targets[self.shard_num::self.n_collaborators]
        test.data = test_dataset.data[self.shard_num::self.n_collaborators]
        test.targets = test_dataset.targets[self.shard_num::self.n_collaborators]

        return {
            "train_loader": torch.utils.data.DataLoader(train, batch_size=self.batch_size, shuffle=True),
            "test_loader": torch.utils.data.DataLoader(test, batch_size=self.batch_size, shuffle=True),
        }
        
