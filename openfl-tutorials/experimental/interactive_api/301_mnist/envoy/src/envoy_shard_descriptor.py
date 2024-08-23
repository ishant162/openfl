import torch

from openfl.experimental.interface.interactive_api import ShardDescriptor


class EnvoyShardDescriptor(ShardDescriptor):
    """Shard descriptor class."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs

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
        train, test = self.download_data()
        return train, test
    
    def get_private_attributes(self):
        """
        Return private attributes in the dict format
        """
        train, test = self.get_dataset()
        batch_size=64
        return {
            "train_loader": torch.utils.data.DataLoader(train, batch_size=batch_size, shuffle=True),
            "test_loader": torch.utils.data.DataLoader(test, batch_size=batch_size, shuffle=True),
        }
        
