#!/usr/bin/env python3
from game.board import Board, ETile
from typing import List
from collections import deque

def detect(board: Board) -> List[List[bool]]:
    """
    Returns 2D matrix containing true for dead squares.

    Dead squares are squares, from which a box cannot possibly
     be pushed to any goal (even if Sokoban could teleport
     to any location and there was only one box).

    You should prune the search at any point
     where a box is pushed to a dead square.

    Returned data structure is
        [board_width] lists
            of [board_height] lists
                of bool values.
    (This structure can be indexed "struct[x][y]"
     to get value on position (x, y).)
    """

    
    w,h=board.width,board.height
    dead=[[True for _ in range(h)] for _ in range(w)]
    q=deque()
    
    # goals are alive, walls are dead
    for x in range(w):
        for y in range(h):
            # get tile type at x,y
            # if its a wall its dead forever
            # if its a goal/target tile, its not dead enqueue for bfs propagation
            tile=board.tile(x, y)
            if ETile.is_wall(tile):
                dead[x][y]=True
            elif ETile.is_target(tile):
                dead[x][y]=False
                q.append((x,y))

    # 4 possible movement directions: left,right, up down
    dirs=[(-1,0),(1,0),(0,-1),(0,1)]
    
    # backwards- if box could be pushed from one square into an alive square
    # then that source square is also alive
    while q:
        x,y=q.popleft()
        
        # try all directions where a box could have been pushed from
        for dx,dy in dirs:
            # if a box ended up at x,y it must have been pushed from sx,sy
            # bythe player standing one square further back at px,py
            sx,sy=x-dx,y-dy         # source position(where box starts)
            px,py=x-2*dx,y-2*dy     # player position(behind the box)
            
            # check if this push is possible
            if not (0<=sx<w and 0<=sy<h and 0<=px<w and 0<=py<h):
                continue
            
            if (ETile.is_wall(board.tile(sx,sy)) or 
                ETile.is_wall(board.tile(px,py))):
                continue
            
            # if the source position was dead but now we found it can reach an alive position
            if dead[sx][sy]:
                dead[sx][sy]=False
                q.append((sx,sy))

    return dead