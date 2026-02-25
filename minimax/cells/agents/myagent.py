#!/usr/bin/env python3
from game.agent import Agent
from game.cells import *

from sys import path
from os.path import dirname
from typing import List, Union, Optional, Dict, Tuple, Set
from math import ceil
# hack for importing from parent package
path.append(dirname(dirname(dirname(__file__))))
from minimax import Minimax
from minimax_templates import *

from random import Random


class CellsGame(HeuristicGame):
    def __init__(self) -> None:
        super().__init__()
        raise NotImplementedError

    def initial_state(self, seed: Optional[int]=0) -> object:
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
    """Example move utility."""
    def add_transfer(self, transfer: Transfer) -> None:
        if all(
            transfer.source != t.source or transfer.target==t.target
            for t in self.transfers
        ):
            self.add_and_combine_transfer(transfer)


class MyAgent(Agent):
    # use a local copy for planning
    # coordinated attacks from multiple border cells
    # solo attacks when it can safely capture
    # routes inner cells toward the border
    # simple but reasonable target priority function
    

    def init_random(self, seed: Union[int, None]) -> None:
        self.random=Random(seed)
        self.verbose=False

    @staticmethod
    def atk_mass_needed(defender_mass: int) -> int:
        #how much mass needs to be sent to almost surely capture the target
        return ceil(defender_mass / Game.ATTACK_MUL) + 1

    @staticmethod
    def def_mass_needed(defender_mass: int) -> int:
        #defensive equivalent
        return ceil(defender_mass * Game.ATTACK_MUL)



    def _build_routing_graph(self, game: Game, me: int) -> List[List[int]]:
        owners=game.owners
        neighbors=game.neighbors
        num_cells=game.num_cells

        # find border cells
        border=[]
        for ci in range(num_cells):
            if owners[ci]==me and any(owners[n] != me for n in neighbors[ci]):
                border.append(ci)

        graph=[[] for _ in range(num_cells)]
        visited=[False] * num_cells

        frontier=set(border)
        for ci in frontier:
            visited[ci]=True

        # BFS from border inward
        while frontier:
            next_frontier=set()
            for ci in frontier:
                for ni in neighbors[ci]:
                    if owners[ni]==me and not visited[ni]:
                        graph[ni].append(ci)  # route ni toward border
                        visited[ni]=True
                        next_frontier.add(ni)
            frontier=next_frontier

        return graph



    def _calculate_target_priority(
        self,
        game: Game,
        target: int,
        attacker: int,
        me: int,
    ) -> float:
        owners=game.owners
        mass=int(game.masses[target])
        owner=owners[target]
        attacker_mass=int(game.masses[attacker])

        # base weight
        if owner==(3 - me):  # enemy
            if (attacker_mass - 1) * Game.ATTACK_MUL>mass:
                weight=4.0  # we can capture it
            else:
                weight=1.0  # too strong, low priority
        elif owner==0:  # neutral
            weight=3.5   # slightly prefer neutrals
        else:             # our own (reinforcement)
            weight=2.0

        # size factor
        size_idx=CellType.get_type_index(mass)
        if owner==me:
            # stronger (bigger) cells are more valuable to reinforce
            weight *= (3 - size_idx)
        else:
            # prefer capturing smaller enemy/neutral cells
            weight *= (size_idx + 1)

        # small neutrals are especially good
        if owner==0 and mass <= 10:
            weight *= 1.3

        # growth bonus
        growth=CellType.get_growth(mass)
        weight += growth * 5.0

        # connectivity – more neighbors=more value / influence
        num_neighbors=len(game.neighbors[target])
        weight += num_neighbors * 3.0

        return weight

    def get_move(self, game: Game) -> List[Transfer]:
        me=game.current_player
        enemy=3 - me
        owners=game.owners
        neighbors=game.neighbors
        num_cells=game.num_cells
        masses=list(game.masses)

        move=SafeMove()

        # all my cells
        my_cells=[i for i, o in enumerate(owners) if o==me]
        if not my_cells:
            return move.get_transfers()

        # routing graph and classification
        routing_graph=self._build_routing_graph(game, me)

        border_cells: List[int]=[]
        inner_cells: List[int]=[]
        for ci in my_cells:
            if any(owners[n] != me for n in neighbors[ci]):
                border_cells.append(ci)
            else:
                inner_cells.append(ci)

        def available(ci: int) -> int:
            # never send everything, always keep at least 1 unit
            return max(0, int(masses[ci]) - 1)

        attacked: Set[int]=set()

        # 1a coordinated attacks from border cells
        target_attackers: Dict[int, List[int]]={}
        for ci in border_cells:
            avail_ci=available(ci)
            if avail_ci <= 0:
                continue
            for ni in neighbors[ci]:
                if owners[ni]==me:
                    continue
                target_attackers.setdefault(ni, []).append(ci)

        coordinated_attacks: List[Tuple[float, int, List[int], int]]=[]

        for target, attackers in target_attackers.items():
            def_mass=int(masses[target])
            needed=self.atk_mass_needed(def_mass)

            total_avail=sum(available(a) for a in attackers)
            if total_avail < needed:
                continue

            avg_priority=sum(
                self._calculate_target_priority(game, target, a, me)
                for a in attackers
            ) / len(attackers)

            if owners[target]==enemy:
                avg_priority *= 1.1

            coordinated_attacks.append((avg_priority, target, attackers, needed))

        coordinated_attacks.sort(reverse=True)

        for priority, target, attackers, needed in coordinated_attacks:
            if target in attacked:
                continue

            total_avail=sum(available(a) for a in attackers)
            if total_avail < needed:
                continue

            attackers=sorted(attackers, key=lambda a: masses[a], reverse=True)
            remaining=needed

            for attacker in attackers:
                if remaining <= 0:
                    break
                avail_ci=available(attacker)
                if avail_ci <= 0:
                    continue
                send=min(avail_ci, remaining)
                if send>0:
                    move.add_transfer(Transfer(attacker, target, send))
                    masses[attacker] -= send
                    remaining -= send

            if remaining <= 0:
                attacked.add(target)

        # 1b solo attacks from border cells
        for ci in border_cells:
            avail_ci=available(ci)
            if avail_ci <= 0:
                continue

            best_target=None
            best_priority=-1.0

            for ni in neighbors[ci]:
                if owners[ni]==me or ni in attacked:
                    continue

                def_mass=int(masses[ni])
                needed=self.atk_mass_needed(def_mass)

                if avail_ci >= needed:
                    priority=self._calculate_target_priority(game, ni, ci, me)
                    if priority>best_priority:
                        best_priority=priority
                        best_target=ni

            if best_target is not None:
                def_mass=int(masses[best_target])
                needed=self.atk_mass_needed(def_mass)

                leftover=avail_ci - needed
                extra=CellType.get_mass_over_min_size(leftover)
                send=needed + max(0, extra)
                send=min(send, avail_ci)

                if send>0:
                    move.add_transfer(Transfer(ci, best_target, int(send)))
                    masses[ci] -= send
                    attacked.add(best_target)

        # ------------------------------------------------------------
        # PHASE 2: inner cells → border
        # ------------------------------------------------------------
        for ci in inner_cells:
            if not routing_graph[ci]:
                continue

            avail_ci=available(ci)
            if avail_ci <= 0:
                continue

            route_targets=routing_graph[ci]

            # prefer border cells that are adjacent to enemy
            border_facing_enemy=[
                rt
                for rt in route_targets
                if rt in border_cells
                and any(owners[n]==enemy for n in neighbors[rt])
            ]

            if border_facing_enemy:
                target=self.random.choice(border_facing_enemy)
            else:
                target=self.random.choice(route_targets)

            send=avail_ci
            if send>0:
                move.add_transfer(Transfer(ci, target, int(send)))
                masses[ci] -= send

        # ------------------------------------------------------------
        # PHASE 3: remaining border mass – opportunistic attacks
        # ------------------------------------------------------------
        for ci in border_cells:
            avail_ci=available(ci)
            if avail_ci <= 0:
                continue

            candidates=[ni for ni in neighbors[ci] if owners[ni] != me]
            if not candidates:
                continue

            enemies=[ni for ni in candidates if owners[ni]==enemy]
            neutrals=[ni for ni in candidates if owners[ni]==0]

            targets=enemies or neutrals
            if not targets:
                continue

            # choose the weakest target
            target=min(targets, key=lambda t: masses[t])

            def_mass=int(masses[target])
            needed=self.atk_mass_needed(def_mass)

            # against enemies, do not chip if we cannot capture
            if owners[target]==enemy and avail_ci < needed:
                continue

            send=avail_ci
            if send>0:
                move.add_transfer(Transfer(ci, target, int(send)))
                masses[ci] -= send

        return move.get_transfers()
