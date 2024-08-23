import torch

from openfl.experimental.interface.interactive_api import ShardDescriptor


class AggregatorShardDescriptor(ShardDescriptor):
    """Shard descriptor class."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def download_data(self):
        """
        Download Watermark MNIST dataset
        """
        from .aggregator_data import watermark_data
        
        my_data = watermark_data

        return my_data

    def get_dataset(self):
        """
        Returns train and test dataset.
        """
        watermark_data = self.download_data()
        return watermark_data
    
    def get_private_attributes(self):
        """
        Return private attributes in the dict format
        """
        watermark_data = self.get_dataset()
        return {
            "watermark_data_loader": torch.utils.data.DataLoader(
                watermark_data, batch_size=50, shuffle=True
            ),
            "pretrain_epochs": 25,
            "retrain_epochs": 25,
            "watermark_acc_threshold": 0.98,
            "watermark_pretraining_completed": False,
        }
