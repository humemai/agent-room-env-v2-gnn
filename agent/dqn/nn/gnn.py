"""A lot copied from https://github.com/migalkin/StarE"""

from typing import Literal
import numpy as np
import torch
from torch_geometric.nn import GCNConv
import torch.nn.functional as F
from .mlp import MLP
from .stare_conv import StarEConvLayer


class GNN(torch.nn.Module):
    """Graph Neural Network model. This model is used to compute the Q-values for the
    memory management and explore policies. This model has N layers of GCNConv or
    StarEConv layers and two MLPs for the memory management and explore policies.

    Attributes:
        entities: List of entities
        relations: List of relations
        embedding_dim: The dimension of the embeddings. This will be the size of the
            input node embeddings.
        num_layers_GNN: The number of layers in the GNN.
        num_hidden_layers_MLP: The number of layers in the MLP.
        device: The device to use.
        entity_embeddings: The entity embeddings.
        relation_embeddings: The relation embeddings.
        convs: The graph convolutional layers.
        entity_to_idx: The entity to index mapping.
        relation_to_idx: The relation to index mapping.
        mlp_mm: The MLP for the memory management policy.
        mlp_explore: The MLP for the explore policy.

    """

    def __init__(
        self,
        entities: list[str],
        relations: list[str],
        gcn_layer_params: dict = {
            "type": "StarE",
            "embedding_dim": 8,
            "num_layers": 2,
            "gcn_drop": 0.1,
            "triple_qual_weight": 0.8,
        },
        relu_between_gcn_layers: bool = True,
        dropout_between_gcn_layers: bool = True,
        mlp_params: dict = {"num_hidden_layers": 2, "dueling_dqn": True},
        device: str = "cpu",
    ) -> None:
        """Initialize the GNN model.

        Args:
            entities: List of entities
            relations: List of relations
            gcn_layer_params: The parameters for the GCN layers
            relu_between_gcn_layers: Whether to apply ReLU activation between GCN layers
            dropout_between_gcn_layers: Whether to apply dropout between GCN layers
            mlp_params: The parameters for the MLPs
            device: The device to use. Default is "cpu".

        """
        super(GNN, self).__init__()
        self.entities = entities
        self.relations = relations
        self.gcn_layer_params = gcn_layer_params
        self.gcn_type = gcn_layer_params["type"].lower()
        self.mlp_params = mlp_params
        self.device = device
        self.embedding_dim = gcn_layer_params["embedding_dim"]

        self.entity_to_idx = {entity: idx for idx, entity in enumerate(self.entities)}
        self.relation_to_idx = {
            relation: idx for idx, relation in enumerate(self.relations)
        }

        self.entity_embeddings = torch.nn.Parameter(
            torch.Tensor(len(self.entities), self.embedding_dim)
        ).to(self.device)
        torch.nn.init.xavier_normal_(self.entity_embeddings)
        # self.entity_embeddings.data[0] = 0  # NOT SURE ABOUT THIS

        phases = 2 * np.pi * torch.rand(len(self.relations), self.embedding_dim // 2)
        self.relation_embeddings = torch.nn.Parameter(
            torch.cat(
                [
                    torch.cat([torch.cos(phases), torch.sin(phases)], dim=-1),
                    torch.cat([torch.cos(phases), -torch.sin(phases)], dim=-1),
                ],
                dim=0,
            )
        )
        # self.relation_embeddings.data[0] = 0  # NOT SURE ABOUT THIS

        self.relu_between_gcn_layers = relu_between_gcn_layers
        self.dropout_between_gcn_layers = dropout_between_gcn_layers
        self.relu = torch.nn.ReLU()
        self.drop = torch.nn.Dropout(self.gcn_layer_params["gcn_drop"])

        if "stare" in self.gcn_type:
            self.gcn_layers = torch.nn.ModuleList(
                [
                    StarEConvLayer(
                        in_channels=self.embedding_dim,
                        out_channels=self.embedding_dim,
                        num_rels=len(relations),
                        gcn_drop=self.gcn_layer_params["gcn_drop"],
                        triple_qual_weight=self.gcn_layer_params["triple_qual_weight"],
                    )
                    for _ in range(self.gcn_layer_params["num_layers"])
                ]
            ).to(self.device)

        elif "vanilla" in self.gcn_type:
            self.gcn_layers = torch.nn.ModuleList(
                [
                    GCNConv(
                        self.embedding_dim,
                        self.embedding_dim,
                        improved=False,
                        add_self_loops=False,
                        normalize=False,
                    )
                    for _ in range(self.gcn_layer_params["num_layers"])
                ]
            ).to(self.device)

            for layer in self.gcn_layers:
                if isinstance(layer, torch.nn.Linear):
                    torch.nn.init.xavier_normal_(layer.weight)
                    if layer.bias is not None:
                        layer.bias.data.zero_()

        else:
            raise ValueError(f"{self.gcn_type} is not a valid GNN type.")

        # self.embedding_dim * 3 accounts for the concatenation of the head, relation,
        # and tail embeddings
        self.mlp_mm = MLP(
            n_actions=3,
            input_size=self.embedding_dim * 3,
            hidden_size=self.embedding_dim,
            device=device,
            **mlp_params,
        )
        self.mlp_explore = MLP(
            n_actions=5,
            input_size=self.embedding_dim,
            hidden_size=self.embedding_dim,
            device=device,
            **mlp_params,
        )

    def process_sample(self, sample: list[list]) -> tuple[
        torch.Tensor,
        torch.Tensor,
        torch.Tensor,
        torch.Tensor,
        torch.Tensor,
        torch.Tensor,
        torch.Tensor,
        torch.Tensor,
    ]:
        r"""Process a sample in a batch.

        Args:
            sample: a sample of working memory. It looks like this:

            [['dep_007', 'atlocation', 'room_000', {'current_time': 2, 'strength': 1}],
            ['agent', 'atlocation', 'room_000', {'current_time': 2, 'strength': 1}],
            ['room_000', 'west', 'wall', {'current_time': 2, 'strength': 1}],
            ['room_000', 'north', 'wall', {'current_time': 2, 'strength': 1.8}],
            ['dep_001',
            'atlocation',
            'room_000',
            {'current_time': 2, 'timestamp': [0, 1]}],
            ['room_000', 'south', 'room_004', {'current_time': 2, 'timestamp': [1]}],
            ['room_000',
            'east',
            'room_001',
            {'current_time': 2, 'timestamp': [0], 'strength': 1}]]

        Returns:
            edge_idx: The shape is [2, num_quadruples]
            edge_type: The shape is [num_quadruples]
            quals: The shape is [3, number of qualifier key-value pairs]

            edge_idx_inv: The shape is [2, num_quadruples]
            edge_type_inv: The shape is [num_quadruples]
            quals_inv: The shape is [3, number of qualifier key-value pairs]

            short_memory_idx: The shape is [number of short-term memories]
                the idx indexes `edge_idx` and `edge_type`
            agent_entity_idx: One scalar value. the idx indexes `entity_embeddings`


        """
        edge_idx = []
        edge_type = []
        quals = []

        edge_idx_inv = []
        edge_type_inv = []
        quals_inv = []

        short_memory_idx = []
        agent_entity_idx = None

        for i, quadruple in enumerate(sample):
            head, relation, tail, qualifiers = quadruple

            if head == "agent":
                agent_entity_idx = self.entity_to_idx[head]

            if tail == "agent":
                agent_entity_idx = self.entity_to_idx[tail]

            edge_idx.append([self.entity_to_idx[head], self.entity_to_idx[tail]])
            edge_type.append(self.relation_to_idx[relation])

            edge_idx_inv.append([self.entity_to_idx[tail], self.entity_to_idx[head]])
            edge_type_inv.append(self.relation_to_idx[relation + "_inv"])

            for q_rel, q_entity in qualifiers.items():

                if q_rel == "timestamp":
                    q_entity_str = str(round(max(q_entity)))
                else:
                    q_entity_str = str(round(q_entity))

                if q_rel == "current_time":
                    short_memory_idx.append(i)

                quals.append(
                    [
                        self.relation_to_idx[q_rel],
                        self.entity_to_idx[q_entity_str],
                        i,
                    ]
                )
                quals_inv.append(
                    [
                        self.relation_to_idx[q_rel],
                        self.entity_to_idx[q_entity_str],
                        i,
                    ]
                )

        edge_idx = (
            torch.tensor(edge_idx, dtype=torch.long, device=self.device)
            .t()
            .contiguous()
        ).to(self.device)
        edge_type = (
            torch.tensor(edge_type, dtype=torch.long, device=self.device)
            .t()
            .contiguous()
        ).to(self.device)
        quals = (
            torch.tensor(quals, dtype=torch.long, device=self.device)
            .t()
            .contiguous()
            .to(self.device)
        )

        edge_idx_inv = (
            torch.tensor(edge_idx_inv, dtype=torch.long, device=self.device)
            .t()
            .contiguous()
        ).to(self.device)
        edge_type_inv = (
            torch.tensor(edge_type_inv, dtype=torch.long, device=self.device)
            .t()
            .contiguous()
        ).to(self.device)
        quals_inv = (
            torch.tensor(quals_inv, dtype=torch.long, device=self.device)
            .t()
            .contiguous()
            .to(self.device)
        )

        short_memory_idx = torch.tensor(short_memory_idx, dtype=torch.long).to(
            self.device
        )
        agent_entity_idx = torch.tensor(agent_entity_idx, dtype=torch.long).to(
            self.device
        )

        return (
            edge_idx,
            edge_type,
            quals,
            edge_idx_inv,
            edge_type_inv,
            quals_inv,
            short_memory_idx,
            agent_entity_idx,
        )

    def process_batch(self, data: np.ndarray) -> tuple[
        torch.Tensor,
        torch.Tensor,
        torch.Tensor,
        torch.Tensor,
        torch.Tensor,
        torch.Tensor,
        torch.Tensor,
    ]:
        r"""Process the data batch.

        Args:
            data: The input data as a batch. This is the same as what the `forward`
                method receives. We will make them in to a batched version of the
                entity embeddings, relation embeddings, edge index, edge type, and
                qualifiers. StarE needs all of them, while vanilla-GCN only needs the
                entity embeddings and edge index.

        Returns:
            edge_idx: The shape is [2, num_quadruples]
            edge_type: The shape is [num_quadruples]
            quals: The shape is [3, number of qualifier key-value pairs]

            edge_idx_inv: The shape is [2, num_quadruples]
            edge_type_inv: The shape is [num_quadruples]
            quals_inv: The shape is [3, number of qualifier key-value pairs]

            short_memory_idx: The shape is [number of short-term memories]
                the idx indexes `edge_idx` and `edge_type`
            agent_entity_idx: The shape is [num batches]
                the idx indexes `entity_embeddings`

            num_short_memories: The number of short-term memories in each sample

        """
        edge_idx = []
        edge_type = []
        quals = []

        edge_idx_inv = []
        edge_type_inv = []
        quals_inv = []

        short_memory_idx = []
        agent_entity_idx = []

        num_short_memories = []

        total_edges = 0
        total_edges_inv = 0

        for sample in data:
            (
                edge_idx_,
                edge_type_,
                quals_,
                edge_idx_inv_,
                edge_type_inv_,
                quals_inv_,
                short_memory_idx_,
                agent_entity_idx_,
            ) = self.process_sample(sample)

            edge_idx.append(edge_idx_)
            edge_idx_inv.append(edge_idx_inv_)

            edge_type.append(edge_type_)
            edge_type_inv.append(edge_type_inv_)

            # Increment quals by the number of edges in previous samples
            quals.append(quals_ + torch.tensor([[0], [0], [total_edges]]))
            quals_inv.append(quals_inv_ + torch.tensor([[0], [0], [total_edges_inv]]))

            # Increment short_memory_idx by the number of edges in previous samples
            short_memory_idx.append(short_memory_idx_ + total_edges)

            agent_entity_idx.append(agent_entity_idx_)

            num_short_memories.append(short_memory_idx_.size(0))

            total_edges += edge_idx_.size(1)
            total_edges_inv += edge_idx_inv_.size(1)

        edge_idx = torch.cat(edge_idx + edge_idx_inv, dim=1)
        edge_type = torch.cat(edge_type + edge_type_inv, dim=0)
        quals = torch.cat(quals + quals_inv, dim=1)

        short_memory_idx = torch.cat(short_memory_idx, dim=0)
        agent_entity_idx = torch.tensor(agent_entity_idx)

        num_short_memories = torch.tensor(num_short_memories, dtype=torch.long).to(
            self.device
        )

        return (
            edge_idx,
            edge_type,
            quals,
            short_memory_idx,
            agent_entity_idx,
            num_short_memories,
        )

    def forward(
        self, data: np.ndarray, policy_type: Literal["mm", "explore"]
    ) -> list[torch.Tensor]:
        """Forward pass of the GNN model.

        Args:
            data: The input data as a batch.
            policy_type: The policy type to use.

        Returns:
            The Q-values. The number of elements in the list is equal to the number of
            samples in the batch. Each element is a tensor of Q-values for the actions
            in the sample. The length of the tensor is equal to the number of actions
            in the sample.

        """
        (
            edge_idx,
            edge_type,
            quals,
            short_memory_idx,
            agent_entity_idx,
            num_short_memories,
        ) = self.process_batch(data)

        entity_embeddings = self.entity_embeddings
        relation_embeddings = self.relation_embeddings

        for layer_ in self.gcn_layers:
            if "stare" in self.gcn_type:
                entity_embeddings, relation_embeddings = layer_(
                    entity_embeddings=entity_embeddings,
                    relation_embeddings=relation_embeddings,
                    edge_idx=edge_idx,
                    edge_type=edge_type,
                    quals=quals,
                )
            elif "vanilla" in self.gcn_type:
                entity_embeddings = layer_(entity_embeddings, edge_idx)
            else:
                raise ValueError(f"{self.gcn_type} is not a valid GNN type.")

            if self.dropout_between_gcn_layers:
                entity_embeddings = self.drop(entity_embeddings)
            if self.relu_between_gcn_layers:
                entity_embeddings = F.relu(entity_embeddings)

        if policy_type == "mm":
            assert num_short_memories.sum() == short_memory_idx.size(0)
            triple = []
            for idx in short_memory_idx:
                triple_ = torch.cat(
                    [
                        entity_embeddings[edge_idx[0, idx]],
                        relation_embeddings[edge_type[idx]],
                        entity_embeddings[edge_idx[1, idx]],
                    ],
                    dim=0,
                )
                triple.append(triple_)

            triple = torch.stack(triple, dim=0)

            q_mm_ = self.mlp_mm(triple)

            q_mm = [
                q_mm_[start : start + num]
                for start, num in zip(
                    num_short_memories.cumsum(0).roll(1), num_short_memories
                )
            ]
            q_mm[0] = q_mm_[: num_short_memories[0]]

            return q_mm

        elif policy_type == "explore":
            node = []
            for idx in agent_entity_idx:
                node_ = entity_embeddings[idx]
                node.append(node_)

            node = torch.stack(node)

            q_explore = self.mlp_explore(node)
            q_explore = [row.unsqueeze(0) for row in list(q_explore.unbind(dim=0))]

            return q_explore

        else:
            raise ValueError(f"{policy_type} is not a valid policy type.")
