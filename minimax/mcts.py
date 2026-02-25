#!/usr/bin/env python3
from typing import Optional, Dict, Any
from math import sqrt, log, inf
from minimax_templates import *




class _Node:
    """
    Internal tree node used by MCTS.
    Stores:
      - game state
      - parent, action that led here
      - children
      - statistics (wins, visits) from the ROOT player's perspective
    """

    def __init__(self, state, parent: Optional["_Node"] = None, action=None):
        self.state = state
        self.parent: Optional[_Node] = parent
        self.action = action  # action taken from parent to reach this node

        self.children: Dict[Any, _Node] = {}
        self.untried_actions = None  # filled lazily

        self.visits: int = 0
        self.wins: float = 0.0  # cumulative reward from root player's POV



class Mcts(Strategy):
    """
    Strategy implementation selecting action
    by Monte Carlo Tree-search with base strategy method.
    """

    def __init__(
        self,
        game: AbstractGame,
        base_strat: Strategy,
        limit: int,
        seed: Optional[int] = None,
    ):
        super().__init__(seed)  # initialize self.seed for simulations
        # Your implementation goes here.

        # self.limit = limit
        # ...
        self.game: AbstractGame = game
        self.base_strat: Strategy = base_strat
        self.limit: int = limit
        # Keep exploration constant; sqrt(2) is standard.
        self.c: float = sqrt(2.0)

    def set_seed(self, seed: int) -> None:
        super().set_seed(seed)
        # set seed for base strategy too!
        # self.base_strat.set_seed(seed)
        self.base_strat.set_seed(seed + 1)

    def _uct_select(self, node: _Node) -> _Node:
        """
        Select a child node using the UCT formula.
        """
        assert node.children, "UCT select called on a leaf without children."
        parent_visits = node.visits

        def uct(child: _Node) -> float:
            if child.visits == 0:
                return inf
            exploitation = child.wins / child.visits
            exploration = self.c * sqrt(log(parent_visits) / child.visits)
            return exploitation + exploration

        # argmax over children
        return max(node.children.values(), key=uct)

    def _expand(self, node: _Node) -> _Node:
        """
        Expand one untried action from the node and return the new child.
        If no expansion is possible, returns the original node.
        """
        if node.untried_actions is None:
            node.untried_actions = self.game.actions(node.state)

        if not node.untried_actions:
            return node  # fully expanded leaf or terminal

        # Pick a random untried action to expand
        idx = self.random.randrange(len(node.untried_actions))
        action = node.untried_actions.pop(idx)

        new_state = self.game.clone(node.state)
        self.game.apply(new_state, action)

        child = _Node(new_state, parent=node, action=action)
        child.untried_actions = self.game.actions(child.state)
        node.children[action] = child
        return child

    def _simulate(self, state, root_player: int) -> float:
        """
        Perform a playout starting from `state` using base_strat,
        and return the outcome from the ROOT player's perspective.
        """
        sim_state = self.game.clone(state)

        # Full playout until terminal state
        while not self.game.is_done(sim_state):
            move = self.base_strat.action(sim_state)
            # In case base_strat returns None (shouldn't normally happen),
            # fall back to a random legal action.
            if move is None:
                actions = self.game.actions(sim_state)
                if not actions:
                    break
                move = self.random.choice(actions)
            self.game.apply(sim_state, move)

        outcome = self.game.outcome(sim_state)
        # outcome is from player 1's perspective; transform to root player's POV
        if root_player == 1:
            return outcome
        else:
            return -outcome

    def _backpropagate(self, node: _Node, reward: float) -> None:
        """
        Backpropagate simulation result from leaf to root.
        `reward` is from the root player's perspective.
        """
        while node is not None:
            node.visits += 1
            node.wins += reward
            node = node.parent

    # ----- public interface -----

    def action(self, state):
        """
        Return best action for given state.
        """
        # Your implementation goes here.
        if self.game.is_done(state):
            return None

        root_state = self.game.clone(state)
        root = _Node(root_state)
        root.untried_actions = self.game.actions(root_state)
        root_player = self.game.player(root_state)

        # If there are no actions, nothing to do.
        if not root.untried_actions:
            return None

        # MCTS main loop
        for _ in range(self.limit):
            node = root

            # SELECTION
            # While fully expanded and non-terminal, move down the tree with UCT.
            while (
                node.untried_actions is not None
                and not node.untried_actions
                and node.children
                and not self.game.is_done(node.state)
            ):
                node = self._uct_select(node)

            # EXPANSION
            if not self.game.is_done(node.state):
                node = self._expand(node)

            # SIMULATION
            reward = self._simulate(node.state, root_player)

            # BACKPROPAGATION
            self._backpropagate(node, reward)

        # After all iterations, choose the child with the highest visit count.
        # This is standard and more stable than choosing by win rate.
        best_child = max(
            root.children.values(), key=lambda n: n.visits
        )
        return best_child.action

