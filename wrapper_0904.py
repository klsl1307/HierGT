# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import torch
import numpy as np
import torch_geometric.datasets
# from ogb.graphproppred import PygGraphPropPredDataset
from ogb.lsc.pcqm4m_pyg import PygPCQM4MDataset
# from ogb.lsc.pcqm4mv2_pyg import PygPCQM4Mv2Dataset
from pcqm4mv2_pyg import PygPCQM4Mv2Dataset ## TODO: avoid changing the ogb package
from dataset_pyg import PygGraphPropPredDataset
import pyximport

pyximport.install(setup_args={'include_dirs': np.get_include()})
import algos

import os
os.environ['PyDEWD_MARN_SLOW_RESOLVE_TIMEOUT'] = '10'  # Set the timeout to 10 seconds (or higher as needed)


def convert_to_single_emb(x, offset=512):
    feature_num = x.size(1) if len(x.size()) > 1 else 1
    feature_offset = 1 + \
        torch.arange(0, feature_num * offset, offset, dtype=torch.long)
    x = x + feature_offset
    return x


def preprocess_item(item):
    edge_attr, edge_index, x, smiles = item.edge_attr, item.edge_index, item.x, item.smiles ## TODO: add smiles
    N = x.size(0)
    x = convert_to_single_emb(x)

    # node adj matrix [N, N] bool
    adj = torch.zeros([N, N], dtype=torch.bool)
    adj[edge_index[0, :], edge_index[1, :]] = True

    # edge feature here
    if len(edge_attr.size()) == 1:
        edge_attr = edge_attr[:, None]
    attn_edge_type = torch.zeros([N, N, edge_attr.size(-1)], dtype=torch.long)
    attn_edge_type[edge_index[0, :], edge_index[1, :]
                   ] = convert_to_single_emb(edge_attr) + 1

    shortest_path_result, path = algos.floyd_warshall(adj.numpy())
    max_dist = np.amax(shortest_path_result)
    # max_dist = 1
    edge_input = algos.gen_edge_input(max_dist, path, attn_edge_type.numpy())
    # edge_input = algos.gen_edge_input(max_dist, adj.numpy(), attn_edge_type.numpy())
    rel_pos = torch.from_numpy((shortest_path_result)).long()
    # rel_pos = torch.from_numpy((adj.numpy())).long()
    attn_bias = torch.zeros(
        [N + 1, N + 1], dtype=torch.float)  # with graph token

    # combine
    item.x = x
    item.adj = adj
    item.attn_bias = attn_bias
    item.attn_edge_type = attn_edge_type
    item.rel_pos = rel_pos
    item.in_degree = adj.long().sum(dim=1).view(-1)
    item.out_degree = adj.long().sum(dim=0).view(-1)
    item.edge_input = torch.from_numpy(edge_input).long()
    item.smiles = smiles ## TODO: add smiles

    return item


class MyGraphPropPredDataset(PygGraphPropPredDataset):
    def download(self):
        super(MyGraphPropPredDataset, self).download()

    def process(self):
        super(MyGraphPropPredDataset, self).process()

    def __getitem__(self, idx):
        if isinstance(idx, int):
            item = self.get(self.indices()[idx])
            item.idx = idx
            return preprocess_item(item)
        else:
            return self.index_select(idx)


class MyPygPCQM4MDataset(PygPCQM4MDataset):
    def download(self):
        super(MyPygPCQM4MDataset, self).download()

    def process(self):
        super(MyPygPCQM4MDataset, self).process()

    def __getitem__(self, idx):
        if isinstance(idx, int):
            item = self.get(self.indices()[idx])
            item.idx = idx
            return preprocess_item(item)
        else:
            return self.index_select(idx)
        
## TODO: add v2
class MyPygPCQM4Mv2Dataset(PygPCQM4Mv2Dataset):
    def download(self):
        super(MyPygPCQM4Mv2Dataset, self).download()

    def process(self):
        super(MyPygPCQM4Mv2Dataset, self).process()

    def __getitem__(self, idx):
        if isinstance(idx, int):
            item = self.get(self.indices()[idx])
            item.idx = idx
            return preprocess_item(item)
        else:
            return self.index_select(idx)


class MyZINCDataset(torch_geometric.datasets.ZINC):
    def download(self):
        super(MyZINCDataset, self).download()

    def process(self):
        super(MyZINCDataset, self).process()

    def __getitem__(self, idx):
        if isinstance(idx, int):
            item = self.get(self.indices()[idx])
            item.idx = idx
            return preprocess_item(item)
        else:
            return self.index_select(idx)
