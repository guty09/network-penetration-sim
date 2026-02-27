\# Test Plan — Network Penetration Simulation (OOP + Actions + Score + Detection + In-Game Log)



\## 1) Overview

This test plan verifies the core gameplay loop, command parsing, room navigation, artifact acquisition rules, detection/score mechanics, in-game session log behavior, and endgame conditions.



\*\*Key behaviors under test\*\*

\- Movement and command normalization (north/south/east/west, n/s/e/w, go/move)

\- Artifact acquisition paths (take/exploit/dump) with prerequisites

\- Monitor Server special rule: cannot leave until `disable alerts`

\- Detection starts at \*\*100\*\* and generally goes \*\*down\*\* on progress

\- Actions add \*\*noise\*\* (small increases) but progress reduces detection

\- Score updates for actions and objectives + speed bonus on victory

\- In-game session log (`log`, `log 50`, `log all`, `log clear`)

\- No external file output (no `session.log` or other artifacts created)



\*\*Non-goals\*\*

\- Real pentest tooling execution (all actions are simulated)

\- Networking or OS-level dependencies (game should run identically across OSes)



---



\## 2) Test Environment

\- Python: 3.10+ recommended (works on 3.9+ if type hints compatible)

\- OS: Windows, macOS, Linux

\- Run method:

&nbsp; - VS Code: `python main.py` in integrated terminal



\*\*Pre-test setup\*\*

\- Ensure game runs without exceptions:

&nbsp; - `python main.py`

\- Confirm no files are created:

&nbsp; - Before running, note directory contents

&nbsp; - After running for a few turns, confirm no new log files exist



---



\## 3) Smoke Tests (Start/Exit)



\### SM-01: Launch game and reach first command prompt

\*\*Steps\*\*

1\. Run `python main.py`

2\. Enter operator name (e.g., `gus`)

3\. Press Enter through prompts until game begins

\*\*Expected\*\*

\- No exceptions/crashes

\- Help + How to Play + Vulnerability Summary pages appear

\- Game shows initial room state and waits for command



\### SM-02: Quit command

\*\*Steps\*\*

1\. At command prompt type `quit`

\*\*Expected\*\*

\- Prints "Session terminated."

\- Program exits cleanly



---



\## 4) Command Normalization Tests



\### CMD-01: Cardinal movement commands

\*\*Steps\*\*

1\. Type: `north`

2\. Type: `south`

3\. Type: `east`

4\. Type: `west`

\*\*Expected\*\*

\- Move occurs only when an exit exists for that direction

\- If no exit: "You cannot go that way."



\### CMD-02: Shorthand movement commands

\*\*Steps\*\*

1\. Type: `n`, then `s`, then `e`, then `w`

\*\*Expected\*\*

\- Same behavior as full direction commands



\### CMD-03: go/move verbs

\*\*Steps\*\*

1\. `go north`

2\. `move e`

\*\*Expected\*\*

\- Works identically to movement commands



\### CMD-04: Unknown commands

\*\*Steps\*\*

1\. Type: `asdf`

\*\*Expected\*\*

\- "Unknown command. Type 'help' to see available commands."



\### CMD-05: get syntax

\*\*Steps\*\*

1\. Type: `get` (no item)

\*\*Expected\*\*

\- "Usage: get <item name>"



---



\## 5) Map and Info Commands



\### UI-01: Map command

\*\*Steps\*\*

1\. Type `map`

\*\*Expected\*\*

\- ASCII map prints

\- Current location is marked with `\*`



\### UI-02: Inventory command

\*\*Steps\*\*

1\. Type `inventory`

\*\*Expected\*\*

\- Shows current inventory (Empty or list)



\### UI-03: Detection command

\*\*Steps\*\*

1\. Type `detection`

\*\*Expected\*\*

\- Prints `Detection: X/100 (LABEL)`



\### UI-04: Help command

\*\*Steps\*\*

1\. Type `help`

\*\*Expected\*\*

\- Prints command list including `log` options



---



\## 6) In-Game Session Log Tests (No files)



\### LOG-01: Basic log output

\*\*Steps\*\*

1\. Type `log`

\*\*Expected\*\*

\- Shows a session log header/footer

\- Contains recent events including TURN lines



\### LOG-02: log 50

\*\*Steps\*\*

1\. Do >15 turns (move/scan/etc.)

2\. Type `log 50`

\*\*Expected\*\*

\- Shows up to last 50 entries (or fewer if not available)



\### LOG-03: log all

\*\*Steps\*\*

1\. Type `log all`

\*\*Expected\*\*

\- Shows all stored events



\### LOG-04: log clear

\*\*Steps\*\*

1\. Type `log clear`

2\. Type `log`

\*\*Expected\*\*

\- Prints "Session log cleared."

\- New log contains only the post-clear message(s) and subsequent turns



\### LOG-05: Ensure no external files

\*\*Steps\*\*

1\. Play 2–3 minutes, use scan/exploit/dump

2\. Check working directory for new files

\*\*Expected\*\*

\- No `session.log` or any new files created by the game



---



\## 7) Room Navigation + Exit Rules



\### NAV-01: Move validation

\*\*Steps\*\*

1\. From Jump Box, attempt a direction not in exits (e.g., `west`)

\*\*Expected\*\*

\- "You cannot go that way."



\### NAV-02: Forced pickup rule for take rooms

\*\*Steps\*\*

1\. Go to Help Desk System

2\. Attempt to leave without `take`

\*\*Expected\*\*

\- Blocked with message requiring the item pickup:

&nbsp; - "You must collect 'low-priv credentials' before leaving..."



\### NAV-03: Exempt room rule

\*\*Steps\*\*

1\. From Jump Box (no item), move freely

\*\*Expected\*\*

\- No forced pickup message



\### NAV-04: Monitor Server leave rule

\*\*Steps\*\*

1\. Enter Monitor Server

2\. Attempt to leave via `west` or `south` without disabling alerts

\*\*Expected\*\*

\- Blocked with "Disable alerts before leaving."



---



\## 8) Artifact Acquisition Tests (take / exploit / dump)



\### ART-01: Take in take-based rooms

\*\*Steps\*\*

1\. Go to Help Desk System

2\. Type `take`

\*\*Expected\*\*

\- Adds `low-priv credentials`

\- Score increases +10 (message printed)

\- Detection decreases (a 🟢 detection line printed)



\### ART-02: Get with correct item name

\*\*Steps\*\*

1\. In Network Segment with visible item

2\. Type `get network map`

\*\*Expected\*\*

\- Same as take: adds item, +score, detection reduced



\### ART-03: Get with wrong item name

\*\*Steps\*\*

1\. In Network Segment (network map visible)

2\. Type `get password dump`

\*\*Expected\*\*

\- "You can't get 'password dump' here."

\- Inventory unchanged



\### ART-04: Exploit only in Web App Server

\*\*Steps\*\*

1\. In Jump Box type `exploit`

\*\*Expected\*\*

\- "Exploit attempt not applicable here."



\### ART-05: Exploit requires low-priv credentials

\*\*Steps\*\*

1\. Go to Web App Server WITHOUT low-priv credentials

2\. Type `exploit`

\*\*Expected\*\*

\- "Exploit blocked: you need low-priv credentials first..."



\### ART-06: Successful exploit path

\*\*Steps\*\*

1\. Ensure you have low-priv credentials

2\. Go to Web App Server

3\. Type `exploit`

\*\*Expected\*\*

\- Adds `SQL injection payload`

\- Score +25

\- Detection reduction message printed

\- If CLI\_DEMO\_ENABLED=True, prints CLI demo block



\### ART-07: Dump File Server requires local admin hash

\*\*Steps\*\*

1\. Go to File Server WITHOUT local admin hash

2\. Type `dump`

\*\*Expected\*\*

\- "Dump blocked: you need the local admin hash first..."



\### ART-08: Successful File Server dump

\*\*Steps\*\*

1\. Obtain local admin hash

2\. Go to File Server

3\. Type `dump`

\*\*Expected\*\*

\- Adds `password dump`

\- Score +30

\- Detection reduced

\- CLI demo block appears if enabled



\### ART-09: Monitor Server dump requires alerts disabled

\*\*Steps\*\*

1\. Go to Monitor Server

2\. Type `dump` before disabling alerts

\*\*Expected\*\*

\- "Dump blocked: alerts are active..."



\### ART-10: Disable alerts then dump ticket

\*\*Steps\*\*

1\. Go to Monitor Server

2\. Type `disable alerts`

3\. Type `dump`

\*\*Expected\*\*

\- alerts\_disabled becomes True

\- Score +20 for disabling alerts

\- Detection reduced significantly

\- Kerberos ticket obtained via dump

\- Score +40 for ticket

\- Detection reduced again



---



\## 9) Detection Mechanics Tests



\### DET-01: Initial detection is 100

\*\*Steps\*\*

1\. Start game and reach first room display

\*\*Expected\*\*

\- Detection prints `100/100 (HIGH)`



\### DET-02: Progress reduces detection

\*\*Steps\*\*

1\. Take any artifact (e.g., low-priv credentials)

\*\*Expected\*\*

\- Detection decreases by expected amount (e.g., 12)



\### DET-03: Noise increases detection slightly

\*\*Steps\*\*

1\. Type `scan` several times

\*\*Expected\*\*

\- Detection increases slightly each time



\### DET-04: Map reduces movement noise

\*\*Steps\*\*

1\. Move around BEFORE network map; note detection changes per move

2\. Acquire network map

3\. Move again; note smaller/noise impact

\*\*Expected\*\*

\- Movement noise is lower after network map



\### DET-05: Alerts disabled reduces noise

\*\*Steps\*\*

1\. Disable alerts

2\. Perform scan/dump in later turns

\*\*Expected\*\*

\- Noise impact reduced vs. before disabling alerts



---



\## 10) Scoring + Turn Counter Tests



\### SCORE-01: Turn counter increments every command

\*\*Steps\*\*

1\. Note turns

2\. Enter any command (`map`, `inventory`, etc.)

\*\*Expected\*\*

\- Turns increment by 1 per command input



\### SCORE-02: Scoring for artifacts

\*\*Steps\*\*

1\. Take low-priv credentials (+10)

2\. Exploit payload (+25)

3\. Dump password dump (+30)

4\. Dump kerberos ticket (+40)

\*\*Expected\*\*

\- Score increases by those increments (messages printed)



\### SCORE-03: Speed bonus triggers only on victory

\*\*Steps\*\*

1\. Win the game

\*\*Expected\*\*

\- Speed bonus is awarded (message printed)

2\. Lose the game

\*\*Expected\*\*

\- No speed bonus awarded



---



\## 11) Endgame Tests



\### END-01: Enter DC without all required artifacts

\*\*Steps\*\*

1\. Go to Domain Controller early (missing items)

\*\*Expected\*\*

\- Fail message listing missing artifacts

\- Mission failed

\- Game over



\### END-02: Enter DC with all artifacts but detection too high

\*\*Steps\*\*

1\. Collect all required items

2\. Keep detection above threshold (e.g., >55 if alerts not disabled)

3\. Enter DC

\*\*Expected\*\*

\- "Flagged at DC entry"

\- Mission failed

\- Game over



\### END-03: Win condition

\*\*Steps\*\*

1\. Collect all required artifacts

2\. Reduce detection under threshold

3\. Enter DC

\*\*Expected\*\*

\- "Access granted. Domain Controller compromised."

\- Mission accomplished

\- Shows final stats



---



\## 12) Regression Checklist (After Changes)

Run these quickly any time you update the code:

\- \[ ] Game starts and prompts for name

\- \[ ] `help`, `map`, `inventory`, `detection`, `log` work

\- \[ ] Monitor Server leave rule still enforced

\- \[ ] Artifact obtain rules still correct (take/exploit/dump)

\- \[ ] No external files created

\- \[ ] DC win/loss conditions still correct



---



\## 13) Known Risks / Watch-outs

\- Detection direction: this version starts at 100 and lowers on progress; ensure any future edits don't accidentally revert it.

\- `log all` can get long; keep the 500-entry cap for `log N` to avoid flooding the terminal.

\- If adding new rooms/items, update:

&nbsp; - REQUIRED\_ITEMS

&nbsp; - room definitions (item + obtain\_method)

&nbsp; - any prerequisite logic in exploit/dump

&nbsp; - vulnerability summary text (optional)

