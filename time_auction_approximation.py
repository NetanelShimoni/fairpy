#!python3

"""
Truthful auction of Heterogeneous Divisible Goods with an approximation algorithm.

References:

    Yonatan Aumann, Yair Dombb, Avinatan Hassidim (2015):
    "Auctioning time: Truthful auctions of heterogeneous divisible goods"
    ACM Transactions on Economics and Computation, 4(1).

Programmers: Naama Berman and Yonatan Lifshitz
Since: 2019-12
"""
import random

from agents import *
from allocations import *
from typing import *
from networkx import *
from math import *

import logging

logger = logging.getLogger(__name__)


def equally_sized_pieces(agents: List[Agent], piece_size: float) -> Allocation:
    """
    Algorithm 1.
    Approximation algorithm of the optimal auction for uniform-size pieces.

    Complexity and approximation:
    - Requires only 2 / l values from each agent.
    - Runs in time polynomial in n + 1 / l.
    - Approximates the optimal welfare by a factor of 2.

    :param agents: A list of Agent objects.
    :param piece_size: Size of an equally sized piece.
    :return: A cake-allocation, not necessarily all the cake will be allocated.

    >>> Alice = PiecewiseConstantAgent([100, 1], "Alice")
    >>> Bob = PiecewiseConstantAgent([2, 90], "Bob")
    >>> equally_sized_pieces([Alice, Bob], 0.5)
    > Alice gets [(0, 1)] with value 100.00
    > Bob gets [(1, 2)] with value 90.00

    >>> Alice = PiecewiseConstantAgent([1, 1, 1, 1, 1], "Alice")
    >>> Bob = PiecewiseConstantAgent([3, 3, 3, 1, 1], "Bob")
    >>> equally_sized_pieces([Alice, Bob], 3 / 5)
    > Bob gets [(0, 3)] with value 9.00
    """
    # Initializing variables and asserting conditions
    num_of_agents = len(agents)
    if num_of_agents == 0:
        raise ValueError("There must be at least one agent")
    if not 0 < piece_size <= 1:
        raise ValueError("Piece size must be between 0 and 1")

    logger.info("Setting delta to 1 - [1 / l] * l.")
    delta = 1 - int(1 / piece_size) * piece_size

    logger.info("Create the partitions P0 = 0-l and Pd = delta-l.")
    # Creating the partition of the pieces that start from 0
    partition_0_l = create_partition(piece_size)
    # Creating the partition of the pieces that start from delta
    partition_delta_l = create_partition(piece_size, start=delta)
    # Merging the partitions to one partition
    all_partitions = partition_0_l + partition_delta_l

    length = max([a.cake_length() for a in agents])
    # Normalizing the partitions to match the form of the pieces allocation of the Agents
    normalize_partitions = [(int(p[0] * length), int(p[1] * length)) for p in all_partitions]
    normalize_partitions_0_l = [(int(p[0] * length), int(p[1] * length)) for p in partition_0_l]
    normalize_partitions_delta_l = [(int(p[0] * length), int(p[1] * length)) for p in partition_delta_l]

    # Evaluating the pieces of the partition for every agent there is
    logger.info("For each piece (in both partitions) and agent: compute the agent's value of the piece.")
    evaluations = {}
    # Get evaluation for every piece
    for piece in normalize_partitions:
        # For every piece get evaluation for every agent
        for agent in agents:
            evaluations[(agent, piece)] = agent.eval(start=piece[0], end=piece[1])
    # Create the matching graph
    # One side is the agents, the other side is the partitions and the weights are the evaluations
    logger.info("Create the partition graphs G - P0 and G - Pd")
    g_0_l = create_matching_graph(agents, normalize_partitions_0_l, evaluations)
    g_delta_l = create_matching_graph(agents, normalize_partitions_delta_l, evaluations)

    # Set the edges to be in order, (Agent, partition)
    logger.info("Compute maximum weight matchings for each graph respectively")
    edges_set_0_l = fix_edges(max_weight_matching(g_0_l))
    edges_set_delta_l = fix_edges(max_weight_matching(g_delta_l))

    logger.info("Choose the heavier among the matchings")
    # Check which matching is heavier and choose it
    if calculate_weight(g_delta_l, edges_set_delta_l) > calculate_weight(g_0_l, edges_set_0_l):
        edges_set = edges_set_delta_l
    else:
        edges_set = edges_set_0_l

    # Find the agents that are in the allocation that was chosen
    chosen_agents = [edge[0] for edge in edges_set]
    # Create allocation
    allocation = Allocation(chosen_agents)
    # Add the edges to the allocation
    for edge in edges_set:
        allocation.set_piece(agent_index=chosen_agents.index(edge[0]), piece=[edge[1]])

    return allocation


def discrete_setting(agents: List[Agent], pieces: List[Tuple[float, float]]) -> Allocation:
    """
    Algorithm 2.
    Approximation algorithm of the optimal auction for a discrete cake with known piece sizes.

    Complexity and approximation:
    - Requires at most 2m values from each agent.
    - Runs in time polynomial in n + log m.
    - Approximates the optimal welfare by a factor of log m + 1.

    :param agents: A list of Agent objects.
    :param pieces: List of sized pieces.
    :return: A cake-allocation.

    >>> Alice = PiecewiseConstantAgent([100, 1], "Alice")
    >>> Bob = PiecewiseConstantAgent([2, 90], "Bob")
    >>> discrete_setting([Alice, Bob], [(0, 1), (1, 2)])
    > Alice gets [(0, 1)] with value 100.00
    > Bob gets [(1, 2)] with value 90.00
    """
    # Set m to be the number of pieces in the given partition
    m = len(pieces)
    # Set r to be log of the number of pieces
    r = int(log(m, 2))

    max_weight = 0
    max_match = None

    logger.info("For every t = 0,...,r create the 2 ^ t-partition, partition sequence of 2 ^ t items.")
    logger.info("Denote the t-th partition by Pt.")
    # Go over the partition by powers of 2
    for t in range(0, r + 1):
        logger.info(f"Iteration t = {t}")
        # Change the partition to be a partition with 2^t size of every piece
        partition_i = change_partition(pieces, t)

        logger.info("For each piece and agent: compute the agent's value of the piece.")
        # Evaluate every piece in the new partition
        evaluations = {}
        # Go over every piece in the partition
        for piece in partition_i:
            # Go over each Agent
            for agent in agents:
                # Evaluate the piece according to the Agent
                evaluations[(agent, piece)] = agent.eval(start=piece[0], end=piece[1])

        logger.info(f"create the partition graph G - Pt={t}")
        # Create the matching graph according to the new partition
        g_i = create_matching_graph(agents, partition_i, evaluations)
        logger.info("Compute a maximum weight matching Mt in the graph GPt")
        # Find the max weight matching of the graph and get the set of edges of the matching
        edges_set = max_weight_matching(g_i)
        # Set the edges to be in order, (Agent, partition)
        edges_set = fix_edges(edges_set)
        # Calculate the sum of the weights in the edges set
        weight = calculate_weight(g_i, edges_set)
        # Check for the max weight
        if weight > max_weight:
            max_weight = weight
            # Keep the edges set of the max weight
            max_match = edges_set

    # Get the agents that are part of the edges of the max weight
    chosen_agents = [edge[0] for edge in max_match]
    # Create the allocation
    allocation = Allocation(chosen_agents)
    # Add the edges to the allocation
    for edge in max_match:
        allocation.set_piece(agent_index=chosen_agents.index(edge[0]), piece=[edge[1]])

    return allocation


def continuous_setting(agents: List[Agent]) -> Allocation:
    """
    Algorithm 3.
    Approximation algorithm of the optimal auction for a continuous cake.

    Complexity and approximation:
    - Requires at most 2n2 values from each agent.
    - Runs in time polynomial in n.
    - Approximates the optimal welfare by a factor of O(log n).

    :param agents: A list of Agent objects.
    :return: A cake-allocation.

    >>> Alice1 = PiecewiseConstantAgent([100, 1], "Alice")
    >>> Alice2 = PiecewiseConstantAgent([100, 1], "Alice")
    >>> continuous_setting([Alice1, Alice2])
    > Alice gets [(0, 2)] with value 101.00
    """
    # set n to be the number of agents
    n = len(agents)
    logger.info("Choose n/2 agents at random. Denote this set by S.")
    # Choose randomly half of the agents
    s = random.choices(agents, k=n//2)
    # Create a new partition
    partitions = set()
    # Add the start to the partition
    partitions.add(0)

    logger.info("For every agent i in S, ask i to divide [0, 1] into 2n intervals of equal worth")
    # Go over all the agents that were chosen
    for a in s:
        start = 0
        # Get pieces with value of 2n
        for i in range(0,2*n):
            end = a.mark(start, a.cake_value()/(2*n))
            # if the piece is out of boundaries we don't add it to the partition
            if end is None:
                break
            end = float("%.4f" % end)
            # Add the piece to the partition
            partitions.add(end)
            start = end

    partitions = list(partitions)
    # Sort the pieces
    partitions = sorted(partitions)

    logger.info("Generate a partition J by taking the union of all boundary points reported by the agents of S.")
    # Turn the list of the pieces into one partition
    start = partitions[0]
    pieces = []
    # Go over all the parts of the partitions and turn it to one partition
    for part in partitions[1:]:
        p = (start, part)
        pieces.append(p)
        start = part

    logger.info("Invoke Algorithm 2 on the rest of the agents and on the sequence of items in J")
    # Get the agents that were nor chosen
    agents = list(set(agents) - set(s))
    # Find the best allocation for those agents with the partition we generated and use Algo 2 to do that
    res = discrete_setting(agents, pieces)
    # Return the allocation
    return res


def create_partition(size: float, start: float=0) -> List[Tuple[float, float]]:
    """
    Used in algorithm 1.
    Creating a partition of [0, 1] with equally sized pieces of given size starting from a given start.
    :param size: The size of the pieces.
    :param start: The location the pieces will start from.
    :return: A partition as described.
    """
    res = []
    end = start + size
    # Iterate until we divide all the cake into pieces
    while end <= 1:
        # add the piece to the list
        res.append((start, end))
        start = end
        end = start + size
    return res


def fix_edges(edges_set: Set[Tuple[Agent, Tuple[float, float]]]) -> Set[Tuple[Agent, Tuple[float, float]]]:
    """
    Used in algorithm 1 and 2.
    Fix the edge format, sometimes the edges are written backwards
    since the matching algorithm does not care about the edge direction.
    Each edge contains agent and a piece, this function will make sure the agent comes first in the edge.
    :param edges_set: A set of edges to fix.
    :return: A copy of the fixed set of edges.
    """
    ret = set()
    # Go over all the edges and check if they are in the right order
    for edge in edges_set:
        # If the partition is first we swap the sides of the edge
        if not isinstance(edge[0], Agent):
            ret.add((edge[1], edge[0]))
        else:
            # The Agent is first and we leave it like that
            ret.add((edge[0], edge[1]))
    # we return the set of edges when all the edges are in the right order of (Agent, partition)
    return ret


def change_partition(partition: List[tuple], t: int) -> List[tuple]:
    """
    Used in algorithm 2.
    Create a partition from original partition where each 2 ^ t pieces are united.
    :param partition: The original partition.
    :param t: Defines the size of the new partition.
    :return: A partition with pieces with 2 ^ t size.
    """
    ret = []
    # Go over all the original partitions with 2^t jumps
    for start in range(0, len(partition) - 2 ** t + 1, 2 ** t):
        end = start + 2 ** t - 1
        # Add the new joined partition to the list
        ret.append((partition[start][0], partition[end][1]))
    return ret


def calculate_weight(g: Graph, edges_set: Set[Tuple[Agent, Tuple[float, float]]]) -> float:
    """
    Used in algorithm 2.
    Calculates the weight of a match over a graph.
    :param g: The graph with all the weights.
    :param edges_set: The edges of the matching - for which we will sum the weight.
    :return: A single number - the total weight.
    """
    ret = 0
    # Go over all the weights of the edges and sum the weights
    for edge in edges_set:
        ret += g.get_edge_data(edge[0], edge[1])['weight']
    return ret


def create_matching_graph(left: List[Agent], right: List[Tuple[float, float]],
                          weights: Dict[Tuple[Agent, Tuple[float, float]], float])-> nx.Graph:
    """
    Used in algorithm 2 and 3.
    Creating a weighted bi-partition graph that represents agents, cake pieces and values.
    :param left: List of agents.
    :param right: List of cake pieces.
    :param weights: A dictionary from agents to pieces - represents the value of each agent to each piece.
    :return: A graph object from the given parameters.
    """
    # Create the graph
    g = nx.DiGraph()
    # Set the left side of the graph to be the Agents
    g.add_nodes_from(left, bipartite=0)
    # Set the right side of the graph to be the partitions
    g.add_nodes_from(right, bipartite=1)
    # Set the edges of the graph with their weights
    for key, value in weights.items():
        g.add_edge(key[0], key[1], weight=value)
    return g


