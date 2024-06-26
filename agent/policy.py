"""Handcrafted / trained policies.

The trained neural network policies are not implemented yet.
"""

from typing import Literal
import random

from humemai.memory import ShortMemory, MemorySystems


def encode_observation(memory_systems: MemorySystems, obs: list[str | int]) -> None:
    """Non RL policy of encoding an observation into a short-term memory.

    At the moment, observation is the same as short-term memory, since this is made for
    RoomEnv-v2.

    Args:
        MemorySystems
        obs: observation as a quadruple: [head, relation, tail, int]

    """
    mem_short = ShortMemory.ob2short(obs)
    memory_systems.short.add(mem_short)


def encode_all_observations(
    memory_systems: MemorySystems, obs_multiple: list[list[str | int]]
) -> None:
    """Non RL policy of encoding all observations into short-term memories.

    Args:
        MemorySystems
        obs_multiple: a list of observations

    """
    assert isinstance(obs_multiple, list), "`obs_multi1ple` should be a list."
    for obs in obs_multiple:
        encode_observation(memory_systems, obs)


def find_agent_current_location(memory_systems: MemorySystems) -> str | None:
    """Find the current location of the agent.

    Use the latest episodic memory about the agent's location.

    Args:
        MemorySystems

    Returns:
        agent_current_location: str | None

    """
    mems_episodic = []
    for mem in memory_systems.get_working_memory():
        if mem[0] == "agent" and mem[1] == "atlocation" and "timestamp" in mem[-1]:
            mems_episodic.append(mem)

    if len(mems_episodic) > 0:
        agent_current_location = mems_episodic[-1][2]  # get the latest one
        return agent_current_location

    return None


def find_visited_locations(
    memory_systems: MemorySystems,
    sort_by: Literal["timestamp", "strength"] = "timestamp",
) -> dict[str, list[str]]:
    """Find the locations that the agent has visited so far.

    Args:
        MemorySystems: MemorySystems
        sort_by: "timestamp" or "strength"

    Returns:
        visited_locations: a list of visited locations

    """
    visited_locations = []

    for mem in memory_systems.get_working_memory():
        if mem[0] == "agent" and mem[1] == "atlocation":
            visited_locations.append(mem[2])


def explore(
    memory_systems: MemorySystems,
    explore_policy: str,
) -> str:
    """Explore the room (sub-graph).

    "random" policy: randomly choose an action.
    "avoid_walls" policy: avoid the walls. This takes into account the agent's current
        location (from episodic) and the memories about the map (from semantic and
        episodic)

    Args:
        memory_systems: MemorySystems
        explore_policy: "random" or "avoid_walls"

    Returns:
        action: The exploration action to take.

    """
    if explore_policy == "random":
        action = random.choice(["north", "east", "south", "west", "stay"])
    elif explore_policy == "avoid_walls":
        agent_current_location = find_agent_current_location(memory_systems)

        # no information about the agent's location
        if agent_current_location is None:
            action = random.choice(["north", "east", "south", "west", "stay"])

        # Get all the memories related to the current location
        mems_map = []

        for mem in memory_systems.get_working_memory():
            if mem[0] == agent_current_location and mem[1] in [
                "north",
                "east",
                "south",
                "west",
            ]:
                mems_map.append(mem)

        # we know the agent's current location but there is no memory about the map
        if len(mems_map) == 0:
            action = random.choice(["north", "east", "south", "west", "stay"])

        else:
            # we know the agent's current location and there is at least one memory
            # about the map and we want to avoid the walls

            to_take = []
            to_avoid = []

            for mem in mems_map:
                if mem[2].split("_")[0] == "room":
                    to_take.append(mem[1])
                elif mem[2] == "wall":
                    if mem[1] not in to_avoid:
                        to_avoid.append(mem[1])

            if len(to_take) > 0:
                action = random.choice(to_take)
            else:
                options = ["north", "east", "south", "west", "stay"]
                for e in to_avoid:
                    options.remove(e)

                action = random.choice(options)

    else:
        raise ValueError("Unknown exploration policy.")

    assert action in ["north", "east", "south", "west", "stay"]

    return action


def manage_memory(
    memory_systems: MemorySystems,
    policy: str,
    mem_short: list,
) -> None:
    """Non RL memory management policy. This function directly manages the long-term
    memory. It tries to balance the number of episodic and semantic memories. Balancing
    is done by trying to keep the equal number of timestamps and strengths.

    Args:
        MemorySystems
        policy: "episodic", "semantic", or "forget"
        mem_short: a short-term memory to be moved into a long-term memory.

    """
    assert policy.lower() in [
        "episodic",
        "semantic",
        "forget",
    ]
    assert memory_systems.short.has_memory(mem_short)
    assert not memory_systems.short.is_empty

    def forget_long_when_full(memory_systems: MemorySystems):
        num_timestamps, num_strengths = memory_systems.long.count_memories()

        if num_timestamps > num_strengths:
            memory_systems.long.forget_by_selection("oldest")

        elif num_timestamps < num_strengths:
            memory_systems.long.forget_by_selection("weakest")

        else:
            if "oldest" == random.choice(["oldest", "weakest"]):
                memory_systems.long.forget_by_selection("oldest")
            else:
                memory_systems.long.forget_by_selection("weakest")

    if policy.lower() == "episodic":
        mem_epi = ShortMemory.short2epi(mem_short)
        check, error_msg = memory_systems.long.can_be_added(mem_epi)
        if check:
            memory_systems.long.add(mem_epi)
        else:
            if error_msg == "The memory system is full!":
                forget_long_when_full(memory_systems)
                memory_systems.long.add(mem_epi)
            else:
                raise ValueError(error_msg)

    elif policy.lower() == "semantic":
        mem_sem = ShortMemory.short2sem(mem_short)
        check, error_msg = memory_systems.long.can_be_added(mem_sem)
        if check:
            memory_systems.long.add(mem_sem)
        else:
            if error_msg == "The memory system is full!":
                forget_long_when_full(memory_systems)
                memory_systems.long.add(mem_sem)
            else:
                raise ValueError(error_msg)

    elif policy.lower() == "forget":
        pass

    else:
        raise ValueError

    memory_systems.short.forget(mem_short)  # don't forget to forget the short memory!


def answer_question(
    memory_systems: MemorySystems,
    policy: str,
    question: list[str | int],
) -> None | str | int:
    """Use the memory systems to answer a question from RoomEnv-v2. It assumes that
    the question is a one-hop query. As we closely follow the cognitive science,
    we only use the working memory answer the questions. The working memory is
    short-term + (partial) long-term memory. The long-term memory used is partial,
    since it can be too big.

    Args:
        MemorySystems
        qa_policy: "random", "latest_strongest", or "strongest_latest".
        question: A quadruple given by RoomEnv-v2, e.g., [laptop, atlocation, ?,
            current_time]

    Returns:
        pred: prediction

    """
    query_idx = question.index("?")
    working = memory_systems.get_working_memory()
    memory_object = working.query(question[:-1] + ["?"])

    if len(memory_object) == 0:
        return None

    mem_latest = memory_object.retrieve_memory_by_qualifier(
        "timestamp", "list", "max", "max"
    )
    mem_strongest = memory_object.retrieve_memory_by_qualifier("strength", "int", "max")

    if policy.lower() == "random":
        return memory_object.retrieve_random_memory()[query_idx]

    elif policy.lower() == "latest_strongest":

        if mem_latest is not None:
            return mem_latest[query_idx]
        elif mem_strongest is not None:
            return mem_strongest[query_idx]
        else:
            return None

    elif policy.lower() == "strongest_latest":

        if mem_strongest is not None:
            return mem_strongest[query_idx]
        elif mem_latest is not None:
            return mem_latest[query_idx]
        else:
            return None

    else:
        raise ValueError("Unknown policy.")
