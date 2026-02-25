#!/usr/bin/env python3
from game.dino import *
from game.agent import Agent


class MyAgent(Agent):
    duck_ticks=0
    jump_ticks=0 
    @staticmethod
    def get_move(game: Game)->DinoMove:
        dino_x=game.dino.x
        dino_y=game.dino.y
        speed=game.speed
        #for how long to be down
        if MyAgent.duck_ticks>0:
            MyAgent.duck_ticks-=1
            return DinoMove.DOWN_RIGHT

        # for how long to fly
        if MyAgent.jump_ticks>0:
            MyAgent.jump_ticks-=1

            # just while in the air
            if not hasattr(MyAgent,"base_speed"):
                MyAgent.base_speed=game.speed
            game.speed+=0.3 

            return DinoMove.UP_RIGHT
        else:
            # if not in jump
            if hasattr(MyAgent,"base_speed"):
                game.speed=MyAgent.base_speed

        
        closest_obstacle=None
        min_dist=float("inf")
        for o in game.obstacles:
            dist=o.rect.x-dino_x
            if 0<dist<min_dist:
                min_dist=dist
                closest_obstacle=o

        if not closest_obstacle:
            return DinoMove.RIGHT

        rect=closest_obstacle.rect
        obs_type=closest_obstacle.type

        
        reaction_distance=120 + 5 * (speed - 5)

        # the middle bird, stay down
        if obs_type==ObstacleType.BIRD1:
            if min_dist<reaction_distance:
                MyAgent.duck_ticks=45 
                return DinoMove.DOWN_RIGHT

        elif obs_type==ObstacleType.BIRD2:
            #dont react, too high
            return DinoMove.RIGHT
        # jump, the closest to the ground
        elif obs_type==ObstacleType.BIRD3:
            if min_dist<reaction_distance+20:
                MyAgent.jump_ticks=20
                return DinoMove.UP_RIGHT

        elif obs_type==ObstacleType.SMALL_CACTUS1:
            if min_dist<reaction_distance:
                MyAgent.jump_ticks=9 
                return DinoMove.UP_RIGHT

        elif obs_type==ObstacleType.SMALL_CACTUS2:
            if min_dist<reaction_distance+10:
                MyAgent.jump_ticks=20
                return DinoMove.UP_RIGHT

        elif obs_type==ObstacleType.SMALL_CACTUS3:
            if min_dist<reaction_distance+25:
                MyAgent.jump_ticks=25
                return DinoMove.UP_RIGHT


        elif obs_type==ObstacleType.LARGE_CACTUS1:
            if min_dist<reaction_distance+10:
                MyAgent.jump_ticks=17 
                return DinoMove.UP_RIGHT

        elif obs_type==ObstacleType.LARGE_CACTUS2:
            if min_dist<reaction_distance+20:
                MyAgent.jump_ticks=23  
                return DinoMove.UP_RIGHT

        elif obs_type==ObstacleType.LARGE_CACTUS3:
            if min_dist<reaction_distance+40:
                MyAgent.jump_ticks=27 
                return DinoMove.UP_RIGHT
        return DinoMove.RIGHT