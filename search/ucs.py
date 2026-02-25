#!/usr/bin/env python3
from search_templates import Problem, Solution
from dataclasses import dataclass, field
from typing import Any, List, Optional
import heapq


@dataclass(order=True)
class Node:
    priority: float
    state: Any = field(compare=False)
    parent: Optional['Node'] = field(compare=False, default=None)
    action: Any = field(compare=False, default=None)
    path_cost: float = field(compare=False, default=0)


    def path(self) -> List[Any]:
        node, actions = self, []
        while node.parent is not None:
            actions.append(node.action)
            node = node.parent
        return list(reversed(actions))

def ucs(problem: Problem) -> Optional[Solution]:
    """Return Solution of the problem solved by UCS search."""
    # Your implementation goes here.
    # start the search, prioroty 0 bcs the cost of the trip=0
    start_node=Node(priority=0,state=problem.initial_state(),parent=None,action=None,path_cost=0)
    frontier=[] #waiting list of nodes
    heapq.heappush(frontier,start_node)
    explored=set()
    # map state->cheapest path cost in frontier
    frontier_costs={start_node.state:0}


    while frontier:
        # take node with lowest cost from the froniter
        node=heapq.heappop(frontier)
        if problem.is_goal(node.state):
            return Solution(actions=node.path(),goal_state=node.state,path_cost=node.path_cost)
        
        explored.add(node.state)
        
        for action in problem.actions(node.state):
            child_state=problem.result(node.state,action)
            cost=node.path_cost+problem.cost(node.state,action)
            #if that condition hasnt already been investigated 
            # or if we've found a cheaper way to do
            # create a new node that represents that child, add it to frontier, update the lowest cost to that state
            if child_state not in explored and (child_state not in frontier_costs or cost<frontier_costs[child_state]):
                child_node=Node(priority=cost,state=child_state,parent=node,action=action,path_cost=cost)
                heapq.heappush(frontier,child_node)
                
                frontier_costs[child_state]=cost


    return None
   
