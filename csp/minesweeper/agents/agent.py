#!/usr/bin/env python3
from game.minesweeper import *
from game.artificial_agent import ArtificialAgent
import sys
from os.path import dirname
from typing import List, Tuple, Optional

sys.path.append(dirname(dirname(dirname(__file__))))
from csp_templates import BooleanCSP, Constraint
from solver import Solver


class Agent(ArtificialAgent):
    def __init__(self, verbose: int) -> None:
        super().__init__(verbose)
        self.solver = Solver()
        self.csp: Optional[BooleanCSP] = None
        self.w = 0
        self.h = 0

        self.seen_visible: set[int] = set()
        self.seen_number_constraints: set[int] = set() 

        self.pending: List[Tuple[int, int, int]] = []  # (x, y, action_type)

    def new_game(self) -> None:
        super().new_game()
        self.csp = None
        self.w = self.h = 0
        self.seen_visible.clear()
        self.seen_number_constraints.clear()
        self.pending.clear()

    def _var(self, x: int, y: int) -> int:
        return y * self.w + x

    def _pos(self, v: int) -> Tuple[int, int]:
        return (v % self.w, v // self.w)

    def _neighbors_vars(self, x: int, y: int, board: Board) -> List[int]:
        res = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if 0 <= nx < board.width and 0 <= ny < board.height:
                    res.append(self._var(nx, ny))
        return res

    def _sync_board_to_csp(self, board: Board) -> None:
        """
        - for visible: set(var, False)
        - for flagged: set(var, True) 
        - for visible constraint: (mines_around of neighbors)
        """
        for (x, y), t in board.generator():
            v = self._var(x, y)

            # flagged -> mine 
            if t.flag and self.csp.value[v] is None:
                self.csp.set(v, True)

            # visible -> safe
            if t.visible and v not in self.seen_visible:
                self.seen_visible.add(v)
                # if visible -> not mine
                if self.csp.value[v] is None:
                    self.csp.set(v, False)

            # constraint 
            if t.visible and t.mines_around > 0 and v not in self.seen_number_constraints:
                self.seen_number_constraints.add(v)
                neigh = self._neighbors_vars(x, y, board)
                self.csp.add_constraint(Constraint(t.mines_around, neigh))

    def _enqueue_inferred_moves(self, board: Board, inferred_vars: List[int]) -> None:
        for v in inferred_vars:
            val = self.csp.value[v]
            x, y = self._pos(v)
            tile = board.tile(x, y)

            if tile.visible:
                continue

            if val is False:
                # safe uncover if not flag
                if not tile.flag and board.is_possible(ActionFactory.get_uncover_action(x, y)):
                    self.pending.append((x, y, ActionFactory.UNCOVER))
            elif val is True:
                # mine -> flag 
                if not tile.flag and board.is_possible(ActionFactory.get_flag_action(x, y)):
                    self.pending.append((x, y, ActionFactory.FLAG))

    def think_impl(self, board: Board, previous_board: Board) -> Action:
        if self.csp is None:
            self.w, self.h = board.width, board.height
            self.csp = BooleanCSP(self.w * self.h)

        self._sync_board_to_csp(board)

        while self.pending:
            x, y, at = self.pending.pop(0)
            if at == ActionFactory.UNCOVER:
                if board.is_possible(ActionFactory.get_uncover_action(x, y)):
                    v = self._var(x, y)
                    if self.csp.value[v] is None:
                        self.csp.set(v, False)
                    return ActionFactory.get_uncover_action(x, y)
            else:
                if board.is_possible(ActionFactory.get_flag_action(x, y)):
                    v = self._var(x, y)
                    if self.csp.value[v] is None:
                        self.csp.set(v, True)
                    return ActionFactory.get_flag_action(x, y)

        # forward checking 
        inferred = self.solver.forward_check(self.csp)
        if inferred is None:
            return ActionFactory.get_advice_action()
        if inferred:
            self._enqueue_inferred_moves(board, inferred)
            if self.pending:
                return self.think_impl(board, previous_board)

        # proof by contradiction 
        v = self.solver.infer_var(self.csp)
        if v != -1:
            inferred2 = self.solver.forward_check(self.csp)
            if inferred2:
                self._enqueue_inferred_moves(board, inferred2)
                if self.pending:
                    return self.think_impl(board, previous_board)

        
        return ActionFactory.get_advice_action()
