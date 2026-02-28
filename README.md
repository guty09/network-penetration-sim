# Cyber Penetration Sim

A text-based cybersecurity red team simulation written in Python.

This project simulates an authorized internal penetration test where the player navigates a corporate network, collects required artifacts, manages detection risk, disables monitoring systems, discovers hosts, and attempts to compromise the final target.

All commands are simulated.
No real tools or system commands are executed.


---

## Features

- CLI-based interactive gameplay
- Object-oriented (OOP) structure
- Detection and scoring mechanics
- Artifact acquisition with prerequisites
- In-memory session logging (no external files created)
- Simulated command execution output
- Host discovery system (scan / hosts / hosts clear)
- Linux-style ping command simulation
- Room-based network reachability logic
- Detection noise vs progress mechanics
- Final target validation logic
- Manual functional test plan included


---

## How to Run

Clone the repository:

git clone https://github.com/guty09/cyber-penetration-sim.git  
cd cyber-penetration-sim  
python main.py  

Requires Python 3.9 or newer.


---

## Objective

1. Collect all required artifacts
2. Reduce detection risk
3. Disable monitoring alerts
4. Discover hosts on the network
5. Enter the final target prepared
6. Avoid detection failure


---

## Commands

Navigation

north  
south  
east  
west  
n  
s  
e  
w  
go <direction>  
move <direction>  


Game commands

scan  
ping <host>  
hosts  
hosts clear  
map  
inventory  
detection  
log  
log 50  
log all  
log clear  
take  
exploit  
dump  
disable alerts  
help  
quit  


---

## Project Structure

cyber-penetration-sim/

main.py  
README.md  
TEST_PLAN.md  
docs/  


---

## Testing

Manual functional testing is documented in detail.

See TEST_PLAN.md

The test plan verifies:

- command parsing
- navigation rules
- artifact logic
- detection mechanics
- scoring
- session log
- host discovery
- ping simulation
- endgame validation


---

## Notes

- This project is for educational use
- No real penetration testing is performed
- No network traffic is generated
- No files are written during gameplay
- Safe to run on any system


---

## Version

Current version: v1.1.0

Includes:

- Host discovery
- Ping simulation
- Improved detection logic
- Extended test plan



