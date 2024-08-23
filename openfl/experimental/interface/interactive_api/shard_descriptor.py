class ShardDescriptor:
    """Shard descriptor class."""

    def get_dataset(self):
        """Defines how the user should retrieve the dataset."""
        raise NotImplementedError

    def get_private_attributes(self):
        """Defines how the user should specify private attributes."""
        raise NotImplementedError
