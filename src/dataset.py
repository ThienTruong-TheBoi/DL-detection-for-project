import os
import pickle
from typing import Tuple

import torch
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, Dataset, Subset


class MalwareDataset(Dataset):
    def __init__(self, benign_dir: str, malware_dir: str):
        self.benign_dir = benign_dir
        self.malware_dir = malware_dir
        self.benign_files = sorted(os.listdir(benign_dir))
        self.malware_files = sorted(os.listdir(malware_dir))

    def __getitem__(self, index: int) -> Tuple[torch.FloatTensor, float]:
        try:
            file_dir = os.path.join(self.benign_dir, self.benign_files[index])
            label = 0.0
        except IndexError:
            file_dir = os.path.join(
                self.malware_dir,
                self.malware_files[index - len(self.benign_files)],
            )
            label = 1.0
        with open(file_dir, "rb") as f:
            file_ = torch.tensor(pickle.load(f))
        return file_, label

    def __len__(self) -> int:
        return len(self.benign_files) + len(self.malware_files)


class UniLabelDataset(Dataset):
    def __init__(self, data_dir: str, is_malware: bool):
        self.data_dir = data_dir
        self.label = float(is_malware)
        self.files = sorted(os.listdir(data_dir))

    def __getitem__(self, index: int) -> Tuple[torch.FloatTensor, float]:
        file_dir = os.path.join(self.data_dir, self.files[index])
        with open(file_dir, "rb") as f:
            file_ = torch.tensor(pickle.load(f))
        return file_, self.label

    def __len__(self) -> int:
        return len(self.files)


def collate_fn(batch):
    xs = pad_sequence([x[0] for x in batch], max_len=4096, padding_value=256)
    ys = torch.tensor([x[1] for x in batch])
    return xs, ys


def pad_sequence(sequences, max_len=None, padding_value=0):
    batch_size = len(sequences)
    if max_len is None:
        max_len = max([s.size(0) for s in sequences])
    out_tensor = sequences[0].new_full((batch_size, max_len), padding_value)
    for i, tensor in enumerate(sequences):
        length = tensor.size(0)
        if max_len > length:
            out_tensor[i, :length] = tensor
        else:
            out_tensor[i, :max_len] = tensor[:max_len]
    return out_tensor


def train_val_test_split(idx, val_size, test_size, shuffle: bool = True):
    tv_idx, test_idx = train_test_split(idx, test_size=test_size, shuffle=shuffle)
    train_idx, val_idx = train_test_split(tv_idx, test_size=val_size, shuffle=shuffle)
    return train_idx, val_idx, test_idx


def make_idx(dataset: Dataset, val_size, test_size):
    num_benign = len(dataset.benign_files)
    num_malware = len(dataset.malware_files)
    benign_idx = range(num_benign)
    malware_idx = range(num_benign, num_benign + num_malware)
    benign_train_idx, benign_val_idx, benign_test_idx = train_val_test_split(
        benign_idx, val_size, test_size
    )
    malware_train_idx, malware_val_idx, malware_test_idx = train_val_test_split(
        malware_idx, val_size, test_size
    )
    train_idx = benign_train_idx + malware_train_idx
    val_idx = benign_val_idx + malware_val_idx
    test_idx = benign_test_idx + malware_test_idx
    return train_idx, val_idx, test_idx


def make_loaders(
    benign_dir: str, malware_dir: str, batch_size: int, val_size, test_size
):
    
    non_train_size = val_size + test_size
    if non_train_size >= 1:
        raise ValueError(
            f"val_size + test_size == {non_train_size}. Please adjust the proportions and try again."
        )
    dataset = MalwareDataset(benign_dir, malware_dir)
    train_idx, val_idx, test_idx = make_idx(dataset, val_size, test_size)
    train_dataset = Subset(dataset, indices=train_idx)
    #val_dataset = Subset(dataset, indices=val_idx)
    test_dataset = Subset(dataset, indices=test_idx)
    train_loader = make_loader(train_dataset, batch_size)
    #val_loader = make_loader(val_dataset, batch_size, shuffle=False)
    test_loader = make_loader(test_dataset, batch_size, shuffle=False)
    
    #test
    testing = MalwareDataset("/home/kali/deep-malware-detection/raw/test/benign","/home/kali/deep-malware-detection/raw/test/malware")
    train1_idx, val1_idx, test1_idx = make_idx(testing, 1, 0)
    val_dataset = Subset(testing, indices=val_idx)
    val_loader = make_loader(val_dataset, batch_size, shuffle=False)
    
    return train_loader, val_loader, test_loader


def make_loader(dataset, batch_size, shuffle=True):
    return DataLoader(
        dataset, batch_size=batch_size, collate_fn=collate_fn, shuffle=shuffle
    )