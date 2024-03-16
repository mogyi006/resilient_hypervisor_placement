# Standard library imports.
import os
os.environ["DGLBACKEND"] = "pytorch"
import random
import itertools
import logging
import datetime
import collections

# Related third party imports.
import pandas as pd
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt

import dgl
import torch
import torch.nn as nn
import torch.nn.functional as F
import sklearn.metrics

# Local application/library specific imports.
import src.logger as logger


def save_model(model, path2model, model_name, **kwargs):
    torch.save(model.state_dict(), path2model + model_name + '.pt')
    logger.save2json(path2model + model_name + '.json', model.parameter_dict)

def load_model(path2model, model_name, **kwargs):
    model_parameter_dict = logger.load_json(path2model + model_name + '.json')
    model = GCN(**model_parameter_dict)
    model.load_state_dict(torch.load(path2model + model_name + '.pt'))
    model.eval()
    return model

def create_dgl_graph(network_simulation):
    # Convert the NetworkX graph to a DGL graph
    dgl_graph = dgl.from_networkx(network_simulation.network_operator.graph)
    # Add the node features
    network_simulation.network_operator.calculate_metrics()
    node_counts = collections.Counter()
    for request in network_simulation.vSDN_requests_ilp:
        node_counts.update(request.switches)
    node_counts = np.array([node_counts[node] for node in network_simulation.network_operator.nodes])

    network_operator_features = [array for array in network_simulation.network_operator.features.values()]

    feat = np.stack(network_operator_features + [node_counts], axis=1)
    feat = feat / feat.max(axis=0)
    feat = torch.tensor(feat, dtype=torch.float32)
    dgl_graph.ndata['features'] = feat
    dgl_graph.ndata['label'] = torch.tensor([
        1 if node in network_simulation.network_operator.active_hypervisors
        else 0 for node in network_simulation.network_operator.graph.nodes])
    return dgl_graph

class GCN(nn.Module):

    def __init__(self, in_feats, hid_feats, out_feats, n_layers):
        super().__init__()
        self.parameter_dict = {
            'in_feats': in_feats,
            'hid_feats': hid_feats,
            'out_feats': out_feats,
            'n_layers': n_layers,
        }
        self.convs = nn.ModuleList()
        self.convs.append(
            dgl.nn.GraphConv(in_feats=in_feats,
                             out_feats=hid_feats,
                             activation=F.relu))
        for i in range(n_layers - 2):
            self.convs.append(
                dgl.nn.GraphConv(in_feats=hid_feats,
                                 out_feats=hid_feats,
                                 activation=F.relu))
        self.convs.append(
            dgl.nn.GraphConv(in_feats=hid_feats,
                             out_feats=out_feats,
                             activation=F.relu))
        self.dropout = nn.Dropout(0.1)

    def forward(self, graph, features):
        h = features
        for i, layer in enumerate(self.convs):
            if i != 0:
                h = self.dropout(h)
            h = layer(graph, h)
        return h

def assign_masks_to_graph(graph,
                          train_ratio=0.6,
                          val_ratio=0.2,
                          shuffle=False,
                          n_graphs=None):
    for ntype in graph.ntypes:
        n_nodes = graph.num_nodes(ntype)
        if n_graphs is not None and n_graphs > 10:
            n_train = int(int(n_graphs * train_ratio) * n_nodes / n_graphs)
            n_val = int(int(n_graphs * val_ratio) * n_nodes / n_graphs)
        else:
            n_train = int(n_nodes * train_ratio)
            n_val = int(n_nodes * val_ratio)

        # create a list of indices for all nodes
        node_indices = list(range(n_nodes))

        if shuffle:
            # randomly shuffle the node indices
            random.shuffle(node_indices)

        # create boolean masks for the training, validation, and test sets
        train_mask = torch.zeros(n_nodes, dtype=torch.bool)
        val_mask = torch.zeros(n_nodes, dtype=torch.bool)
        test_mask = torch.zeros(n_nodes, dtype=torch.bool)

        # assign the node indices to the masks
        train_mask[node_indices[:n_train]] = True
        val_mask[node_indices[n_train:n_train + n_val]] = True
        test_mask[node_indices[n_train + n_val:]] = True

        # assign the masks to the graph
        graph.nodes[ntype].data['train_mask'] = train_mask
        graph.nodes[ntype].data['val_mask'] = val_mask
        graph.nodes[ntype].data['test_mask'] = test_mask

    return

def evaluate(model, graph, features, labels, mask):
    model.eval()
    with torch.no_grad():
        logits = model(graph, features)
        if logits.size(1) == 1:
            logits = logits[mask].squeeze()
            labels = labels[mask].float()
            logits_pred = logits > 0.5
            correct = torch.sum(logits_pred == labels)
        else:
            logits = logits[mask]
            labels = labels[mask]
            _, indices = torch.max(logits, dim=1)
            correct = torch.sum(indices == labels)
        return correct.item() * 1.0 / len(labels)

class weighted_MSELoss(nn.Module):
    def __init__(self, weight=1.0, threshold=0.45):
        super().__init__()
        self.weight = weight
        self.threshold = threshold
    def forward(self,inputs,targets):
        return torch.mean(
            ((inputs - targets)**2) * (1 + (targets > self.threshold).float() * self.weight))

def train_gnn(graph, n_layers=2, n_hidden=100, lr=1e-2, weight_decay=5e-3, n_epochs=21, weight = 1.0, threshold=0.45):
    """
    Trains a GNN model on the given graph `g`.

    Args:
    - g (dgl.DGLGraph): the graph to train on
    - n_hidden (int): the number of hidden units in the GNN model
    - lr (float): the learning rate to use for training
    - n_epochs (int): the number of epochs to train for

    Returns:
    - gnn_model (SAGE): the trained GNN model
    """
    features = graph.ndata['features']
    labels = graph.ndata['label']
    n_features = features.shape[1]
    # n_labels = int(labels.max().item() + 1)
    n_labels = 1

    # gnn_model = dgl.nn.SAGEConv(in_feats=n_features, out_feats=n_labels, aggregator_type='mean', feat_drop=0.1, activation=F.relu)
    gnn_model = GCN(in_feats=n_features,
                    hid_feats=n_hidden,
                    out_feats=n_labels,
                    n_layers=n_layers)
    # define loss function and optimizer
    if n_labels == 1:
        # loss_fcn = nn.BCEWithLogitsLoss(pos_weight=torch.tensor([1.0]))
        # loss_fcn = nn.MSELoss()
        loss_fcn = weighted_MSELoss(weight=weight, threshold=threshold)
    else:
        loss_fcn = nn.CrossEntropyLoss(weight=torch.tensor([1.0, 1.0]))
    optimizer = torch.optim.Adam(gnn_model.parameters(),
                                 lr=lr,
                                 weight_decay=weight_decay)

    training_logs = {
        'loss': [],
        'val_loss': [],
    }

    for epoch in range(n_epochs):
        gnn_model.train()
        # forward propagation by using all nodes
        logits = gnn_model(graph, features)
        # print(logits)
        # compute loss
        if logits.size(1) == 1:
            loss = loss_fcn(logits[graph.ndata['train_mask']].squeeze(),
                            labels[graph.ndata['train_mask']].float())
        else:
            loss = loss_fcn(logits[graph.ndata['train_mask']],
                            labels[graph.ndata['train_mask']])
        
        training_logs['loss'].append(loss.item())

        # backward propagation
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if epoch % 50 == 0:
            acc = evaluate(gnn_model, graph, features, labels,
                           graph.ndata['val_mask'])
            print("Epoch {:05d} | Loss {:.4f} | Accuracy {:.4f} ".format(
                epoch, loss.item(), acc))
        
        # validation
        gnn_model.eval()
        with torch.no_grad():
            logits = gnn_model(graph, features)
            if logits.size(1) == 1:
                loss = loss_fcn(logits[graph.ndata['val_mask']].squeeze(),
                                labels[graph.ndata['val_mask']].float())
            else:
                loss = loss_fcn(logits[graph.ndata['val_mask']],
                                labels[graph.ndata['val_mask']])
            training_logs['val_loss'].append(loss.item())


    print(classification_report(gnn_model, graph, features, labels, graph.ndata['test_mask']))

    return gnn_model, training_logs

def classification_report(model, graph, features, labels, mask):
    model.eval()
    with torch.no_grad():
        logits = model(graph, features)
        if logits.size(1) == 1:
            logits = logits[mask].squeeze()
            labels = labels[mask].float()
            indices = logits > 0.5
            correct = torch.sum(indices == labels)
        else:
            logits = logits[mask]
            labels = labels[mask]
            _, indices = torch.max(logits, dim=1)
            correct = torch.sum(indices == labels)
        return sklearn.metrics.classification_report(labels, indices)

def plot_roc(model, graph, features, labels, mask):
    model.eval()
    with torch.no_grad():
        logits = model(graph, features)
        if isinstance(mask, list):
            for m in mask:
                fpr, tpr, _ = sklearn.metrics.roc_curve(labels[m].detach().numpy(), logits[m].detach().numpy())
                plt.plot(fpr, tpr)
        else:
            fpr, tpr, _ = sklearn.metrics.roc_curve(labels[mask].detach().numpy(), logits[mask].detach().numpy())
            plt.plot(fpr, tpr)
        plt.xlabel('False Positive Rate')
        plt.ylabel('True Positive Rate')
        plt.title('ROC Curve')
        plt.grid(True)
        plt.show()

def plot_score_distribution(model, graph, features, labels):
    model.eval()
    with torch.no_grad():
        scores = model(graph, features)
        # Separate scores for label 0 and label 1
        scores_label_0 = scores[labels == 0]
        scores_label_1 = scores[labels == 1]

        # Plot histograms for each class
        plt.hist(scores_label_0.detach().numpy(), bins=50, alpha=0.5, label='Label 0', color='blue')
        plt.hist(scores_label_1.detach().numpy(), bins=50, alpha=0.5, label='Label 1', color='orange')

        plt.xlabel('Score')
        plt.ylabel('Count')
        plt.title('Score Distribution')
        plt.grid(True)
        plt.show()


def plot_precision_recall_curve(model, graph, features, labels):
    model.eval()
    with torch.no_grad():
        scores = model(graph, features)
        precision, recall, thresholds = sklearn.metrics.precision_recall_curve(labels.detach().numpy(), scores.detach().numpy())
        area_under_curve = sklearn.metrics.auc(recall, precision)

        fig, ax = plt.subplots(ncols=2, figsize=(12, 4))
        ax[0].plot(thresholds, precision[:-1], label='Precision')
        ax[0].plot(thresholds, recall[:-1], label='Recall')
        ax[0].set_xlabel('Threshold')
        ax[0].set_ylabel('Precision/Recall')
        ax[0].set_title('Precision-Recall Threshold Curve')
        ax[0].legend()
        ax[1].plot(recall, precision, label='Precision-Recall Curve (AUC = {:.2f})'.format(area_under_curve))
        ax[1].set_xlabel('Recall')
        ax[1].set_ylabel('Precision')
        ax[1].set_title('Precision-Recall Curve')
        ax[1].legend()