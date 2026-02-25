#!/usr/bin/env python3
import heapq
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple
from search_templates import Solution, HeuristicProblem


@dataclass(order=True)
class Node:
    f:float         #total estimated cost g+h used for priority ordering
    g:float=field(compare=False)        #cost from start to this node
    state:Any=field(compare=False)      # current state
    actions:List[Any]=field(compare=False, default_factory=list)


def AStar(prob: HeuristicProblem) -> Optional[Solution]:
    """Return Solution of the problem solved by AStar search."""
    # Your implementation goes here.

    # start node has path cost g=0 and total cost f=g+h=h
    # get start state, computate heuristic value, create node f=h,g=0, empty act
    start=prob.initial_state()
    start_h=prob.estimate(start)
    start_node=Node(start_h,0,start,[])

    # contains all discovered nodes that hvaent been expanded and do minheap
    frontier: List[Node]=[]
    heapq.heappush(frontier,start_node)

    # store best known g-cost for each visited state
    best_cost={start: 0}
    explored=set()


    
    while frontier:
        # the node with the lowest estimated total cost-expanded first
        node=heapq.heappop(frontier)

        # skip if already expanded
        if node.state in explored:
            continue
        explored.add(node.state)
        if prob.is_goal(node.state):
            return Solution(node.actions,node.state,node.g)

        # each possible move
        # apply action-new state, cost of this action, new cumulative path cost
        for action in prob.actions(node.state):
            child_state=prob.result(node.state,action)
            step_cost=prob.cost(node.state,action)
            g_new=node.g+step_cost
            f_new=g_new+prob.estimate(child_state)

            # if new path is better or state is new
            # add the child node if its not visited before or i cheaper path to it 
            if child_state not in best_cost or g_new < best_cost[child_state]:
                best_cost[child_state]=g_new
                new_actions=node.actions+[action]
                heapq.heappush(frontier,Node(f_new, g_new, child_state, new_actions))


    return None
