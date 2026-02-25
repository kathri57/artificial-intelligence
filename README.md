# AI I

This repository contains practical tasks for the [Artificial Intelligence 1](http://ktiml.mff.cuni.cz/~bartak/ui/) course, that is based on book by Russel and Norvig [Artificial Intellignece: A Modern Approach, 4th Edition](https://www.pearson.com/us/higher-education/program/Russell-Artificial-Intelligence-A-Modern-Approach-4th-Edition/PGM1263338.html). Tasks are designed to review AI algorithms and use them to play games.

---

## Requirements
All assignments will be written in python. Task were created for python 3.9 however there should not be any problems with backward compatibility. You can solve all assignments while working exclusively with python standard library, however for game visualizations you will need to install modul [pygame](https://www.pygame.org/wiki/GettingStarted).
For installation you can use [pip](https://pypi.org/project/pip/):

    python3 -m pip install -U pygame --user

If you need more detailed, platform-specific instructions you can visit [pygame-GettingStarted](https://www.pygame.org/wiki/GettingStarted).


## Games & My Solutions

Below is an overview of the games included and the main AI approaches I implemented:

| Game                                                                     | My Approach                       |
| ------------------------------------------------------------------------ | --------------------------------- |
| [Dino](dino/README.md)                                                   | rule-based agent                  |
| [Pac-Man](search/README.md#assignment-2-uniform-cost-search-and-pac-man) | uniform-cost search               |
| [Sokoban](search/README.md#assignment-3-a-and-sokoban)                   | A* with custom heuristics         |
| [Cell Wars](minimax/README.md)                                           | minimax / Monte Carlo tree search |
| [Minesweeper](csp/README.md)                                             | backtracking search for CSPs      |


The focus is on my personal implementations, the agent logic in myagent, and the AI algorithms applied in each game, rather than the original assignments themselves.

## Notes

- All solutions are my own work and have been tested in the local environment.

- Some visualization and helper files are included to make the games playable.

- This repo is meant as a showcase of my understanding and experiments with AI algorithms.




