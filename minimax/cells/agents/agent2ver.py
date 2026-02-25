#!/usr/bin/env python3
from game.agent import Agent
from game.cells import *

from sys import path
from os.path import dirname
from random import Random
from typing import List, Union, Optional, Dict, Tuple, Set
from math import ceil

# Hack to allow importing from the top-level folder
path.append(dirname(dirname(dirname(__file__))))
from minimax_templates import HeuristicGame  # for skeleton compatibility


class CellsGame(HeuristicGame):
    """
    Adapter required by the provided skeleton.
    This class is NOT used by MyAgent in this implementation.
    It is safe to leave it unimplemented for ReCodEx.
    """

    def __init__(self) -> None:
        super().__init__()
        raise NotImplementedError

    def initial_state(self, seed: Optional[int] = 0) -> object:
        raise NotImplementedError

    def clone(self, state: Game) -> object:
        raise NotImplementedError

    def player(self, state: Game) -> int:
        raise NotImplementedError

    def actions(self, state: Game) -> list:
        raise NotImplementedError

    def apply(self, state: Game, action) -> None:
        raise NotImplementedError

    def is_done(self, state: Game) -> bool:
        raise NotImplementedError

    def outcome(self, state: Game) -> float:
        raise NotImplementedError

    def evaluate(self, state: Game) -> float:
        raise NotImplementedError


class SafeMove(TransferMove):
    """
    TransferMove variant that allows at most one transfer
    from each source cell (per target).
    """

    def add_transfer(self, transfer: Transfer) -> None:
        if all(
            transfer.source != t.source or transfer.target == t.target
            for t in self.transfers
        ):
            self.add_and_combine_transfer(transfer)


class MyAgent(Agent):
    """
    Enhanced agent combining aggression with Ranger-inspired tactics.
    
    Key improvements over simple version:
    - Better attack mass calculation (like Ranger)
    - Graph-based routing (inspired by Ranger/Destroyer)
    - Coordinated multi-cell attacks
    - Smart target prioritization
    """

    def init_random(self, seed: Union[int, None]) -> None:
        self.random = Random(seed)
        self.verbose = False

    @staticmethod
    def atk_mass_needed(defender_mass: int) -> int:
        """Calculate exact mass needed to capture (Ranger-style)."""
        return ceil(defender_mass / Game.ATTACK_MUL) + 1

    @staticmethod
    def def_mass_needed(defender_mass: int) -> int:
        """Calculate defense mass equivalent."""
        return ceil(defender_mass * Game.ATTACK_MUL)

    def _build_routing_graph(self, game: Game, me: int) -> List[List[int]]:
        """
        Build graph for routing inner cells to border.
        Similar to Destroyer's approach but simplified.
        """
        owners = game.owners
        neighbors = game.neighbors
        num_cells = game.num_cells
        
        # Find border cells
        border = []
        for ci in range(num_cells):
            if owners[ci] == me and any(owners[n] != me for n in neighbors[ci]):
                border.append(ci)
        
        # BFS from border inward
        graph = [[] for _ in range(num_cells)]
        visited = [False] * num_cells
        
        frontier = set(border)
        for ci in frontier:
            visited[ci] = True
        
        while frontier:
            next_frontier = set()
            for ci in frontier:
                for ni in neighbors[ci]:
                    if owners[ni] == me and not visited[ni]:
                        graph[ni].append(ci)  # Route toward border
                        visited[ni] = True
                        next_frontier.add(ni)
            frontier = next_frontier
        
        return graph

    def _calculate_target_priority(
        self, 
        game: Game, 
        target: int, 
        attacker: int,
        me: int
    ) -> float:
        """
        Calculate priority for attacking a target.
        Inspired by Destroyer's priority system.
        """
        owner = game.owners[target]
        mass = int(game.masses[target])
        attacker_mass = int(game.masses[attacker])
        
        # Base weight
        if owner == (3 - me):
            # Enemy cell
            if (attacker_mass - 1) * Game.ATTACK_MUL > mass:
                weight = 4  # Can capture
            else:
                weight = 1  # Too strong
        elif owner == 0:
            weight = 3  # Neutral
        else:
            weight = 2  # Our own cell (reinforcement)
        
        # Size consideration
        size_idx = CellType.get_type_index(mass)
        if owner == me:
            # Prefer larger cells for reinforcement
            weight *= (3 - size_idx)
        else:
            # Prefer capturing smaller enemy/neutral cells
            weight *= (size_idx + 1)
        
        # Growth bonus
        growth = CellType.get_growth(mass)
        weight += growth * 5
        
        # Connectivity bonus
        num_neighbors = len(game.neighbors[target])
        weight += num_neighbors * 3
        
        return weight

    def get_move(self, game: Game) -> List[Transfer]:
        me = game.current_player
        enemy = 3 - me
        owners = game.owners
        masses = game.masses
        neighbors = game.neighbors
        num_cells = game.num_cells

        move = SafeMove()

        # Get all our cells
        my_cells = [i for i, o in enumerate(owners) if o == me]
        if not my_cells:
            return move.get_transfers()

        # Build routing graph
        routing_graph = self._build_routing_graph(game, me)

        # Classify cells
        border_cells = []
        inner_cells = []
        for ci in my_cells:
            if any(owners[n] != me for n in neighbors[ci]):
                border_cells.append(ci)
            else:
                inner_cells.append(ci)

        # Track what we've attacked
        attacked = set()

        # ------------------------------------------------------------
        # PHASE 1: Border cell attacks (coordinated + solo)
        # ------------------------------------------------------------
        
        # Group targets by potential attackers
        target_attackers: Dict[int, List[int]] = {}
        for ci in border_cells:
            avail = max(0, masses[ci] - 1)
            if avail <= 0:
                continue
            
            for ni in neighbors[ci]:
                if owners[ni] == me:
                    continue
                target_attackers.setdefault(ni, []).append(ci)

        # Evaluate coordinated attacks
        coordinated_attacks = []
        for target, attackers in target_attackers.items():
            def_mass = int(masses[target])
            needed = self.atk_mass_needed(def_mass)
            
            total_avail = sum(max(0, masses[a] - 1) for a in attackers)
            if total_avail >= needed:
                # Calculate average priority
                avg_priority = sum(
                    self._calculate_target_priority(game, target, a, me)
                    for a in attackers
                ) / len(attackers)
                
                coordinated_attacks.append((avg_priority, target, attackers, needed))
        
        # Execute best coordinated attacks
        coordinated_attacks.sort(reverse=True)
        
        for priority, target, attackers, needed in coordinated_attacks:
            if target in attacked:
                continue
            
            # Check if still possible
            total_avail = sum(max(0, masses[a] - 1) for a in attackers)
            if total_avail < needed:
                continue
            
            # Distribute attack
            attackers.sort(key=lambda a: masses[a], reverse=True)
            remaining = needed
            
            for attacker in attackers:
                if remaining <= 0:
                    break
                avail = max(0, masses[attacker] - 1)
                send = int(min(avail, remaining))
                if send > 0:
                    move.add_transfer(Transfer(attacker, target, send))
                    masses[attacker] -= send  # Update for next iteration
                    remaining -= send
            
            attacked.add(target)

        # Solo attacks from border cells
        for ci in border_cells:
            avail = max(0, masses[ci] - 1)
            if avail <= 0:
                continue
            
            # Find best target
            best_target = None
            best_priority = -1
            
            for ni in neighbors[ci]:
                if owners[ni] == me or ni in attacked:
                    continue
                
                def_mass = int(masses[ni])
                needed = self.atk_mass_needed(def_mass)
                
                # Can we capture alone?
                if avail >= needed:
                    priority = self._calculate_target_priority(game, ni, ci, me)
                    if priority > best_priority:
                        best_priority = priority
                        best_target = ni
            
            if best_target is not None:
                def_mass = int(masses[best_target])
                needed = self.atk_mass_needed(def_mass)
                
                # Send needed + bit extra from leftover
                leftover = avail - needed
                extra = CellType.get_mass_over_min_size(leftover)
                send = int(needed + max(0, extra))
                
                if send > 0:
                    move.add_transfer(Transfer(ci, best_target, send))
                    masses[ci] -= send
                    attacked.add(best_target)

        # ------------------------------------------------------------
        # PHASE 2: Route inner cells to border
        # ------------------------------------------------------------
        
        for ci in inner_cells:
            if not routing_graph[ci]:
                continue
            
            avail = max(0, masses[ci] - 1)
            if avail <= 0:
                continue
            
            # Pick best route target (prefer border cells with enemies)
            route_targets = routing_graph[ci]
            
            # Prioritize border cells that face enemies
            border_facing_enemy = [
                rt for rt in route_targets 
                if rt in border_cells and any(owners[n] == enemy for n in neighbors[rt])
            ]
            
            if border_facing_enemy:
                target = self.random.choice(border_facing_enemy)
            else:
                target = self.random.choice(route_targets)
            
            # Send most of available mass
            send = int(avail)
            if send > 0:
                move.add_transfer(Transfer(ci, target, send))
                masses[ci] -= send

        # ------------------------------------------------------------
        # PHASE 3: Use leftover border mass
        # ------------------------------------------------------------
        
        for ci in border_cells:
            avail = max(0, masses[ci] - 1)
            if avail <= 0:
                continue
            
            # Attack any non-friendly neighbor
            candidates = [(ni, owners[ni]) for ni in neighbors[ci] if owners[ni] != me]
            if not candidates:
                continue
            
            # Prioritize: enemy > neutral
            enemies = [ni for ni, o in candidates if o == enemy]
            neutrals = [ni for ni, o in candidates if o == 0]
            
            targets = enemies if enemies else neutrals
            if not targets:
                continue
            
            # Pick weakest target
            target = min(targets, key=lambda t: masses[t])
            
            # Send all leftover
            send = int(avail)
            if send > 0:
                move.add_transfer(Transfer(ci, target, send))

        return move.get_transfers()
