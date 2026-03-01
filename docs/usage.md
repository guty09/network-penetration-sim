# Usage

## Requirements

- Python 3.9 or newer
- Terminal / command prompt

## Running the Program

Clone the repository:

git clone https://github.com/guty09/network-penetration-sim.git
cd network-penetration-sim

Run the program:

python main.py

## Basic Gameplay

The game is a text-based simulation of an authorized internal penetration test.

The player moves through a simulated corporate network, collects required artifacts, manages detection level, and attempts to compromise the final target.

Each turn the player enters a command to perform an action.

## Movement Commands

north  
south  
east  
west  

These commands move between connected rooms if access is allowed.

Short versions may also work:

n  
s  
e  
w  

## Simulation Commands

scan  
ping  
hosts  
hosts clear  
inventory  
take  
use  

These commands are simulated and do not run real system tools.

## Detection System

Some actions increase detection level.

If detection becomes too high, the mission fails.

Some actions can reduce detection.

## Goal

Collect all required artifacts, disable monitoring if needed, and reach the final target before detection reaches the limit.

## Notes

This program is a simulation for educational purposes.  
All commands are internal to the program and no real network or system commands are executed.