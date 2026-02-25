#!/usr/bin/env python3
from game.controllers import PacManControllerBase
from game.pacman import Game, DM


# from game.pac_gui import PacView
import sys
from os.path import dirname

# hack for importing from parent package
sys.path.append(dirname(dirname(dirname(__file__))))
from search_templates import *
from ucs import ucs

# hint: class PacManProblem(Problem)...
#       ... Ucs.search(problem)



from typing import List
import random

class PacManProblem(Problem):
    def __init__(self, game: Game, start: int, goals: List[int], 
                 avoid_ghosts: bool = True, ghost_safety_distance: int = 5):
        self.game=game
        self.start=start
        self.goals=set(goals)
        self.avoid_ghosts=avoid_ghosts
        self.ghost_safety_distance=ghost_safety_distance
        
    def initial_state(self):
        return self.start
    
    def actions(self, state):
        #all possible actions from current stat
        actions=[]
        neighbors=self.game._graph[state].neighbors
        
        for action,next_state in enumerate(neighbors):
            if next_state!=-1:  #-1 means no node in that direction
                actions.append(action)
        return actions
    
    def result(self, state, action):
        #resulting state from taking action in state
        return self.game._graph[state].neighbors[action]
    
    def is_goal(self, state):
        return state in self.goals
    
    def cost(self, state, action):
        #compute cost for moving to next state 
        #includes ghost and goal bonuses
        next_state=self.result(state, action)
        cost=1.0  # base cost movemnt
        
        #add penalty for moving near ghosts
        if self.avoid_ghosts:
            ghost_penalty=self._ghost_penalty(next_state)
            cost+=ghost_penalty
            
        goal_bonus=self._goal_proximity_bonus(next_state)
        cost-=goal_bonus
        
        # small penalty for changing direction frequently
        cost+=0.1
        
        return max(0.1, cost) #always positive cost

    def _ghost_penalty(self, node: int) -> float:
        penalty=0.0
        for i in range(Game.NUM_GHOSTS):
            if not self.game.is_in_lair(i):
                ghost_loc=self.game.get_ghost_loc(i)
                distance=self.game.get_path_distance(node, ghost_loc)
                
                if self.game.is_edible(i):
                    #ssmall bonus for edible ghosts
                    if distance<=8:
                        penalty-=2.0/(distance+1)
                else:
                    # heavy penalty for dangerous ghosts
                    if distance<=self.ghost_safety_distance:
                        penalty+=(self.ghost_safety_distance-distance)**2*10
                
        return penalty
    
    def _goal_proximity_bonus(self, node: int) -> float:
        if not self.goals:
            return 0.0
            
        min_distance=min(self.game.get_path_distance(node,goal) 
                          for goal in self.goals)
        return 1.0/(min_distance+1)


class MyAgent(PacManControllerBase):
    def __init__(self, human: bool = False, seed: int = 0, verbose: bool = False) -> None:
        super().__init__(human, seed, verbose)
        
        # You can initialize your own class variables here.

        self.last_action=None
        self.current_goal=None
        self.failed_goals=set() #keep track of goals unreachable
        self.plan=[]
        self.ticks_since_replan=0 #counter to know when to replan
        
        self.ghost_safety_distance=6
        self.replan_interval=3  
        self.power_pill_activation_distance=10 #if ghost is close go for power pill

    def tick(self, game: Game) -> None:
        # Your implementation goes here.

        # Dummy implementation: move in a random direction.
        # You won't live long this way


        if game._eating_time>0 or game.dying_time>0:
            return
            
        self.ticks_since_replan+=1
        
        if (self.ticks_since_replan>=self.replan_interval or 
            not self.plan or 
            self._should_replan(game)):
            
            self._replan(game)
            self.ticks_since_replan=0
        
        #execute next action fro current plan
        if self.plan:
            next_action=self.plan.pop(0)
            self.pacman.set(next_action)
            self.last_action=next_action
        else:
            #choose any possible direction fallback
            directions=game.get_possible_pacman_dirs(False)
            if directions:
                if self._ghosts_are_close(game,4):
                    safe_dir=self._get_safe_direction(game,directions)
                    if safe_dir is not None:
                        self.pacman.set(safe_dir)
                        self.last_action=safe_dir
                    else:
                        action=self.random.choice(directions)
                        self.pacman.set(action)
                        self.last_action=action
                else:
                    action=self.random.choice(directions)
                    self.pacman.set(action)
                    self.last_action=action

    def _get_safe_direction(self,game: Game, directions: List[int]) -> int:
        pac_loc=game.pac_loc
        safest_dir=None
        max_distance=-1
        
        for direction in directions:
            next_node=game.get_neighbor(pac_loc, direction)
            if next_node!=-1:
                #minimum distance to any dangerous ghost from next position
                min_ghost_dist=float('inf')
                for i in range(Game.NUM_GHOSTS):
                    if not game.is_edible(i) and not game.is_in_lair(i):
                        ghost_dist=game.get_path_distance(next_node, game.get_ghost_loc(i))
                        min_ghost_dist=min(min_ghost_dist, ghost_dist)
                
                if min_ghost_dist>max_distance:
                    max_distance=min_ghost_dist
                    safest_dir=direction
        
        return safest_dir

    def _should_replan(self, game: Game)->bool:
        #decide if ucs plan snhould be recalculated?
        if not self.current_goal:
            return True
            
        pac_loc = game.pac_loc
        
        #replan if ghost became dangerous nearby
        if self._ghosts_are_close(game,3):
            return True
                
        #replan if we reached our goal
        if pac_loc==self.current_goal:
            return True
            
        #replan if current goal is no longer valid
        if self.current_goal in self._get_pill_goals(game):
            pill_index=game.get_pill_index(self.current_goal)
            if pill_index!=-1 and not game.check_pill(pill_index):
                return True
                
        if self.current_goal in self._get_power_pill_goals(game):
            power_pill_index=game.get_power_pill_index(self.current_goal)
            if power_pill_index!=-1 and not game.check_power_pill(power_pill_index):
                return True
        
        #fruit disappeared  triggers replanning
        if self.current_goal==game.fruit_loc and game.fruit_loc==-1:
            return True
            
        return False

    def _replan(self, game: Game) -> None:
        #recalc ucs plan based on curent st
        start=game.pac_loc
        goals=self._select_goals(game)
        
        if not goals:
            self.plan=[]
            self.current_goal=None
            return
            
        #create problem instance
        problem=PacManProblem(
            game,start,goals, 
            avoid_ghosts=True,
            ghost_safety_distance=self.ghost_safety_distance
        )
        
        solution=ucs(problem)
        if solution and solution.actions:
            self.plan=solution.actions
            #the goal is the last state in the solution path
            # track the primary goal instead
            self.current_goal=goals[0] if goals else None
        else:
            self.plan=[]
            self.current_goal=None
            if goals:
                self.failed_goals.add(goals[0])
            if len(self.failed_goals)>5:
                self.failed_goals.clear()

    def _select_goals(self, game: Game)->List[int]:
        #decide which goals are worth pursuing rn
        goals=[]
        pac_loc=game.pac_loc
        
        #PRIORITET
        #edible ghosts
        edible_ghost_goals=self._get_edible_ghost_goals(game)
        if edible_ghost_goals:
            goals.extend(edible_ghost_goals)
        
        #power pills when ghosts are close
        if self._ghosts_are_close(game, distance=8):
            power_pill_goals=self._get_power_pill_goals(game)
            if power_pill_goals:
                goals.extend(power_pill_goals)
        
        #normal pills
        pill_goals=self._get_pill_goals(game)
        if pill_goals:
            goals.extend(pill_goals)
            
        #fruit
        fruit_goal=self._get_fruit_goal(game)
        if fruit_goal!=-1:
            goals.append(fruit_goal)
            
        #power pills as backup
        if not goals:
            power_pill_goals=self._get_power_pill_goals(game)
            if power_pill_goals:
                goals.extend(power_pill_goals)
        
        #remove recently failed goals
        #if still no goals,clear failed goals and try again
        goals = [g for g in goals if g not in self.failed_goals]
        if not goals and self.failed_goals:
            self.failed_goals.clear()
            return self._select_goals(game)
        
        


        goals.sort(key=lambda g: (
            self._goal_priority(game,g),
            game.get_path_distance(pac_loc,g)
        ))
        
        return goals[:2]



    def _get_edible_ghost_goals(self, game: Game) -> List[int]:
        #get locations of edible ghosts
        goals=[]
        for i in range(Game.NUM_GHOSTS):
            if (game.is_edible(i) and not game.is_in_lair(i) and game.get_edible_time(i)>10):
                goals.append(game.get_ghost_loc(i))
        return goals

    def _get_power_pill_goals(self, game: Game) -> List[int]:
        return game.get_active_power_pills_nodes()

    def _get_pill_goals(self, game: Game) -> List[int]:
        return game.get_active_pills_nodes()

    def _get_fruit_goal(self, game: Game) -> int:
        return game.fruit_loc if game.fruit_loc!=-1 else -1

    def _ghosts_are_close(self, game: Game, distance: int) -> bool:
        #check if any dangerous ghost is close
        pac_loc=game.pac_loc
        for i in range(Game.NUM_GHOSTS):
            if (not game.is_edible(i) and not game.is_in_lair(i)):
                ghost_dist=game.get_path_distance(pac_loc,game.get_ghost_loc(i))
                if ghost_dist<=distance:
                    return True
        return False

    def _goal_priority(self, game: Game, goal: int) -> int:
        #calculate priority for a goal 
        #lower is better
        #edible ghosts have highest priority
        for i in range(Game.NUM_GHOSTS):
            if (game.is_edible(i) and game.get_ghost_loc(i)==goal):
                return 1
                
        #ppills when ghosts are close
        if (goal in game.get_active_power_pills_nodes() and self._ghosts_are_close(game, 8)):
            return 2
            
        if goal==game.fruit_loc:
            return 3
            
        if goal in game.get_active_power_pills_nodes():
            return 4
        return 5
