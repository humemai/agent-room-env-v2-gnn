# Agent for RoomEnv-v2

## Prerequisites

1. A unix or unix-like x86 machine
1. python 3.10 or higher.
1. Running in a virtual environment (e.g., conda, virtualenv, etc.) is highly
   recommended so that you don't mess up with the system python.
1. Install the requirements by running `pip install -r requirements.txt`

## Jupyter Notebooks

- [Training our agent (and their hyperparameters)](train-dqn.ipynb)
- [Running trained models](run-trained-models.ipynb)

## RoomEnv-v2

| An illustration of a hidden state $s_{t}$ (in white) and partial observation $o_{t}$ (in gray). |
| :---------------------------------------------------------------------------------------------: |
|                              ![](./figures/room-layout-xl-gnn.png)                              |

| A hidden state $s_{t}$ (in white) and partial observation $o_{t}$ (in gray) represented as a KG. |
| :----------------------------------------------------------------------------------------------: |
|                             ![](./figures/room-layout-kg-xl-gnn.png)                             |

## HumemAI-Unified Agent

| A visualization depicting the two steps in training. |
| :--------------------------------------------------: |
|             ![](./figures/gnn-steps.png)             |

| A forward-pass example of StarE-GCN, $\text{MLP}^{\text{mm}}$, and $\text{MLP}^{\text{explore}}$ |
| :----------------------------------------------------------------------------------------------: |
|                              ![](./figures/gnn-explore-and-mm.png)                               |

| An example of the agent's (HumemAI-Unified with $capacity=192$) memory $\bm{M}_{t=99}$. |
| :-------------------------------------------------------------------------------------: |
|                    ![](./figures/memory-systems-example-xl-gnn.png)                     |

## Training Results

| Capacity | Agent Type          | Phase 1   | Phase 2       |
| -------- | ------------------- | --------- | ------------- |
| 12       | HumemAI-Unified     | N/A       | 152 (±7)      |
|          | **HumemAI**         | 105 (±37) | **160 (±30)** |
|          | Baseline            | N/A       | 144 (±14)     |
| 24       | **HumemAI-Unified** | N/A       | **233 (±34)** |
|          | HumemAI             | 127 (±26) | 214 (±64)     |
|          | Baseline            | N/A       | 138 (±52)     |
| 48       | **HumemAI-Unified** | N/A       | **341 (±21)** |
|          | HumemAI             | 118 (±18) | 235 (±37)     |
|          | Baseline            | N/A       | 200 (±15)     |
| 96       | **HumemAI-Unified** | N/A       | **466 (±37)** |
|          | HumemAI             | N/A       | 209 (±87)     |
|          | Baseline            | N/A       | 155 (±77)     |
| 192      | **HumemAI-Unified** | N/A       | **482 (±14)** |
|          | HumemAI             | N/A       | 176 (±115)    |
|          | Baseline            | N/A       | 144 (±68)     |

## Jupyter Notebooks

- [Training our agent (and their hyperparameters)](train-dqn.ipynb)
- [Running trained models](run-trained-models.ipynb)

## RoomEnv-v2

| An illustration of a hidden state $s_{t}$ (in white) and partial observation $o_{t}$ (in gray). |
| :---------------------------------------------------------------------------------------------: |
|                              ![](./figures/room-layout-xl-gnn.png)                              |

| A hidden state $s_{t}$ (in white) and partial observation $o_{t}$ (in gray) represented as a KG. |
| :----------------------------------------------------------------------------------------------: |
|                             ![](./figures/room-layout-kg-xl-gnn.png)                             |

## HumemAI-Unified Agent

| A visualization depicting the two steps in training. |
| :--------------------------------------------------: |
|             ![](./figures/gnn-steps.png)             |

| A forward-pass example of StarE-GCN, $\text{MLP}^{\text{mm}}$, and $\text{MLP}^{\text{explore}}$ |
| :----------------------------------------------------------------------------------------------: |
|                              ![](./figures/gnn-explore-and-mm.png)                               |

| An example of the agent's (HumemAI-Unified with $capacity=192$) memory $\bm{M}_{t=99}$. |
| :-------------------------------------------------------------------------------------: |
|                    ![](./figures/memory-systems-example-xl-gnn.png)                     |

## Training Results

| Capacity | Agent Type          | Phase 1   | Phase 2       |
| -------- | ------------------- | --------- | ------------- |
| 12       | HumemAI-Unified     | N/A       | 152 (±7)      |
|          | **HumemAI**         | 105 (±37) | **160 (±30)** |
|          | Baseline            | N/A       | 144 (±14)     |
| 24       | **HumemAI-Unified** | N/A       | **233 (±34)** |
|          | HumemAI             | 127 (±26) | 214 (±64)     |
|          | Baseline            | N/A       | 138 (±52)     |
| 48       | **HumemAI-Unified** | N/A       | **341 (±21)** |
|          | HumemAI             | 118 (±18) | 235 (±37)     |
|          | Baseline            | N/A       | 200 (±15)     |
| 96       | **HumemAI-Unified** | N/A       | **466 (±37)** |
|          | HumemAI             | N/A       | 209 (±87)     |
|          | Baseline            | N/A       | 155 (±77)     |
| 192      | **HumemAI-Unified** | N/A       | **482 (±14)** |
|          | HumemAI             | N/A       | 176 (±115)    |
|          | Baseline            | N/A       | 144 (±68)     |
