#!/usr/bin/env python3
from functools import lru_cache
from game.action import *
from game.board import *
from game.artificial_agent import ArtificialAgent
from dead_square_detector import detect
from typing import List, Union
import sys
from time import perf_counter
from os.path import dirname
import math

# hack for importing from parent package
sys.path.append(dirname(dirname(dirname(__file__))))
from astar import AStar
from search_templates import HeuristicProblem


class MyAgent(ArtificialAgent):
    """
    Logic implementation for Sokoban ArtificialAgent.

    See ArtificialAgent for details.
    """

    def __init__(self, optimal, verbose) -> None:
        super().__init__(optimal, verbose)  # recommended

    def new_game(self) -> None:
        """Agent got into a new level."""
        super().new_game()  # recommended

    @staticmethod
    def think(
        board: Board, optimal: bool, verbose: bool
    ) -> List[Union[EDirection, Action]]:
        """
        Code your custom agent here.
        You should use your A* implementation.

        You can find example implementation (without use of A*)
        in simple_agent.py.
        """

        prob = SokobanProblem(board)
        solution = AStar(prob)
        if not solution:
            return None

        return [a.dir for a in solution.actions]



class SokobanProblem(HeuristicProblem):
    """HeuristicProblem wrapper of Sokoban game."""

    def __init__(self, initial_board: Board) -> None:
        # Your implementation goes here.
        # Hint: __init__(self, initial_board) -> None:
        self.initial_board = initial_board.clone()
        self.dead = detect(initial_board)

        #goals are static, never move, precompute their positions
        self.goals = []
        for x in range(self.initial_board.width):
            for y in range(self.initial_board.height):
                tile=self.initial_board.tile(x, y)
                if ETile.is_target(tile):
                    self.goals.append((x, y))


    def initial_state(self) -> Union[Board, StateMinimal]:
        # Your implementation goes here.
        # Hint: return self.initial_board
        return self.initial_board

    
    def actions(self, state: Union[Board, StateMinimal]) -> List[Action]:
        # Your implementation goes here.
        possible=[]

        # try all 4 movement directions
        for d in EDirection:
            a=Move.or_push(state,d)


            if not a.is_possible(state):
                continue

            # if this action is push check wehere box would end up
            # if it would end up on dead sq, we prune this action
            if isinstance(a, Push):
                sx,sy=state.sokoban 

                bx_new=sx+2*d.dx
                by_new=sy+2*d.dy
                # check bounds
                if 0<=bx_new<state.width and 0<=by_new<state.height:
                    if self.dead[bx_new][by_new]:
                        continue

            possible.append(a)

        return possible

    
    def result(
        self, state: Union[Board, StateMinimal], action: Action
    ) -> Union[Board, StateMinimal]:
        # Your implementation goes here.

        new_state=state.clone()
        action.perform(new_state)

        return new_state

    
    def is_goal(self, state: Union[Board, StateMinimal]) -> bool:
        # Your implementation goes here.
        return state.is_victory()

   
    def cost(self, state: Union[Board, StateMinimal], action: Action) -> float:
        # Your implementation goes here.
        return 1.0

    
    def estimate(self, state: Union[Board, StateMinimal]) -> float:
        """
        Heuristic estimate of the remaining cost to reach a goal.

        - If any box is on a dead square, the state is unsolvable -> return infinity.
        - Otherwise, compute the minimal total Manhattan distance of assigning
          each box to a distinct goal (minimum matching).
        """

        boxes = []

        # Collect all box positions, and check for dead-square boxes.
        for x in range(state.width):
            for y in range(state.height):
                tile = state.tile(x, y)
                if ETile.is_box(tile):
                    # If a box is already on a dead square, this state is unsolvable.
                    if self.dead[x][y]:
                        return math.inf
                    boxes.append((x, y))

        # No boxes left -> already solved.
        if not boxes:
            return 0.0

        n = len(boxes)
        m = len(self.goals)

        # Sanity check: normally number of goals equals number of boxes.
        if m == 0:
            return 0.0

        # Precompute Manhattan distances between each box and each goal.
        dist = [
            [abs(bx - gx) + abs(by - gy) for (gx, gy) in self.goals]
            for (bx, by) in boxes
        ]

        @lru_cache(maxsize=None)
        def dp(i: int, mask: int) -> int:
            """
            Dynamic programming over subsets (bitmask) to find minimal
            total assignment cost of boxes to goals.

            i    - index of the box we are assigning now,
            mask - bitmask of goals that are already taken (1 = taken).
            """
            if i == n:
                # All boxes have been assigned to some goal.
                return 0

            best = math.inf
            for g in range(m):
                if not (mask & (1 << g)):
                    # Assign box i to goal g and recurse for the next box.
                    candidate = dist[i][g] + dp(i + 1, mask | (1 << g))
                    if candidate < best:
                        best = candidate
            return best

        return float(dp(0, 0))