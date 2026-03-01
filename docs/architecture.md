# Architecture

## Overview

This project is a text-based cybersecurity red team simulation written in Python.  
The program is built using object-oriented programming to keep the code organized and easier to maintain.

## Object-Oriented Design

Object-oriented programming is a way of designing programs using objects that contain both data and behavior.  
The main OOP concepts include classes, objects, encapsulation, inheritance, and polymorphism.

This project mainly uses classes, objects, and encapsulation to organize the game logic and manage the program state.  
Inheritance and polymorphism were not required, but the program could be expanded in the future to include them.

The program uses separate classes to represent the player, rooms, detection system, and game controller.

- Room class stores description, exits, and items
- Player class stores inventory, score, and detection level
- DetectionMeter class controls alert level
- Game class controls the main loop and rules

## Game Loop

The game runs inside a main loop that continues until the mission is completed or failed.

Each turn:
- show location
- read command
- process command
- update state
- check win/fail

A command parser normalizes input so commands like "north" and "n" are treated the same.

## Game State

The program tracks:

- inventory
- score
- detection level
- current room

Some actions require items before they can be used, which simulates simple access control.

## Detection System

A detection meter simulates monitoring during a penetration test.

Actions such as scanning, exploiting, or moving increase detection.  
Some actions reduce detection.

If detection becomes too high, the mission fails.

## Command Simulation

Commands such as scan and ping are simulated.

They do not run real tools, but display output similar to command-line utilities.

This keeps the program safe while making the game feel realistic.

## Notes

Object-oriented programming was used to keep the program structured and easier to expand.

## Diagram

The architecture diagram for this project is stored in the diagrams directory.

docs/diagrams/architecture.mmd

The diagram shows the relationship between the Game, Player, Room, and DetectionMeter classes.