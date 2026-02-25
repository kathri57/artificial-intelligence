#!/usr/bin/env python3
from minimax_templates import *
from typing import Optional, Tuple, List
import math


class Minimax(Strategy):
    """Strategy implementation selecting action by minimax with alpha-beta pruning method."""

    def __init__(
        self, game: HeuristicGame, limit: int=0, seed: Optional[int]=None
    ) -> None:
        super().__init__(seed)  # initialize self.seed for simulations
        # Your implementation goes here.
        self.game=game
        self.limit=limit

    def action(self, state) -> object:
        """
        Return best action for given state.
        """
        # Your implementation goes here.
        player=self.game.player(state)  
        best_value=-math.inf
        best_action=None
        
        actions=self.game.actions(state)
        self.random.shuffle(actions)  # randomize order to avoid predictable play
        
        for action in actions:
            # clone the state and apply the action
            new_state=self.game.clone(state)
            self.game.apply(new_state, action)
            
            # recursively evaluate the action
            value=self._minimax(new_state, player, 1, -math.inf, math.inf, False)
            
            # update best action
            if value>best_value:
                best_value=value
                best_action=action
        
        return best_action

    def _minimax(self, state, root_player: int, depth: int, alpha: float, beta: float, maximizing_player: bool) -> float:
        """
        Minimax algorithm with alpha-beta pruning.
        Returns the heuristic value of the state.
        """
        # check if game is over
        if self.game.is_done(state):
            outcome=self.game.outcome(state)
            # prioritize faster wins and slower losses
            # root player is always considered as maximizing from roots perspective
            if root_player!=1:
                outcome=-outcome

            if outcome>0: 
                return 1000-depth  
            elif outcome<0: 
                return -1000+depth
            else:  
                return 0  
        
        # depth limit reached, use heuristic evaluation
        if self.limit>0 and depth>=self.limit:
            val=self.game.evaluate(state)  
            if root_player==1:
                return val
            else:
                return -val

        
        # current player from state
        current_player=self.game.player(state)
        is_root_player_turn=(current_player==root_player)
        
        if is_root_player_turn:  # root player's turn maximizing from root's perspective
            value=-math.inf
            actions=self.game.actions(state)
            
            for action in actions:
                # clone the state and apply the action
                new_state=self.game.clone(state)
                self.game.apply(new_state, action)
                
                # recursive call for the next level
                child_value=self._minimax(new_state, root_player, depth + 1, alpha, beta, not is_root_player_turn)
                value=max(value, child_value)
                
                # alpha-beta pruning
                alpha=max(alpha, value)
                if value>=beta:
                    break  # Beta cutoff
                    
            return value
        else:  # opponent's turn , minimizing from root's perspective
            value=math.inf
            actions=self.game.actions(state)
            
            for action in actions:
                new_state=self.game.clone(state)
                self.game.apply(new_state, action)
        
                child_value=self._minimax(new_state, root_player, depth + 1, alpha, beta, not is_root_player_turn)
                value=min(value, child_value)
                
                # Alpha-beta pruning
                beta=min(beta, value)
                if value <= alpha:
                    break  # alpha cutoff
                    
            return value