# Agustin's Network Penetration Simulation
# Object-Oriented Text-Based Cybersecurity Game


"""
Network Penetration Simulation (OOP + Actions + Score + Speed Bonus)

Core behavior:
- Detection starts at 100/100 (HIGH).
- Detection goes DOWN when you make progress (collect artifacts / disable alerts).
- Actions create small "noise" (Detection may rise slightly), but the goal is to reduce it.

New features in this version:
- ZERO external files (no session.log, no file toggles)
- In-game session log (memory only):
    - log            -> show last 15 events
    - log 50         -> show last 50 events
    - log all        -> show all events
    - log clear      -> clear the in-game log
- Safe simulated CLI output (no real tools):
    - CLI_DEMO_ENABLED = True/False
- Linux-style simulated ping + host discovery list (memory only):
    - ping <host>    -> simulated ping output (Linux-like)
    - hosts          -> show discovered hosts
    - hosts clear    -> clear discovered hosts
    - scan + ping automatically discover hosts

This is a simulation (not real pentest tooling).
"""

from __future__ import annotations

import random
import string
import sys
import time
import subprocess
from dataclasses import dataclass, field
from typing import Optional


# -----------------------------
# Feature toggles (NO FILE LOGGING)
# -----------------------------
CLI_DEMO_ENABLED = True  # True = show simulated CLI commands; False = quieter story mode


# -----------------------------
# Game constants / content
# -----------------------------
REQUIRED_ITEMS: set[str] = {
    "network map",
    "low-priv credentials",
    "local admin hash",
    "SQL injection payload",
    "password dump",
    "Kerberos ticket",
}

ITEM_DESCRIPTIONS: dict[str, str] = {
    "network map": "Infrastructure diagram - reduces operational noise and movement risk",
    "low-priv credentials": "Support account credentials - your initial foothold",
    "local admin hash": "Cached credential hash - enables privileged access paths",
    "SQL injection payload": "Simulated exploit artifact - needed to progress the chain",
    "password dump": "Extracted credential archive - reveals privileged access paths",
    "Kerberos ticket": "Golden ticket - the key to domain compromise",
}

EXEMPT_ROOMS: set[str] = {"Jump Box", "Domain Controller", "Monitor Server"}


# -----------------------------
# Command normalization
# -----------------------------
DIRECTION_SYNONYMS = {
    "n": "north",
    "north": "north",
    "s": "south",
    "south": "south",
    "e": "east",
    "east": "east",
    "w": "west",
    "west": "west",
}

ACTION_SYNONYMS = {
    "help": "help",
    "h": "help",
    "?": "help",
    "map": "map",
    "m": "map",
    "inventory": "inventory",
    "inv": "inventory",
    "i": "inventory",
    "quit": "quit",
    "q": "quit",
    "exit": "quit",
    "take": "take",
    "t": "take",
    "disable": "disable_alerts",
    "d": "disable_alerts",
    "scan": "scan",
    "exploit": "exploit",
    "dump": "dump",
    "detection": "detection",
    "risk": "detection",
    "log": "log",
    "logs": "log",
    "hosts": "hosts",
    "ping": "ping",
}


def normalize_command(raw: str) -> tuple[str, Optional[str]]:
    """
    Normalize user input into (action, argument).

    Supports:
    - Movement: north/south/east/west, n/s/e/w, go <dir>, move <dir>
    - Actions: take, get <item>, scan, exploit, dump, ping <host>, disable alerts
    - Info: inventory, detection, map, help, quit
    - Log: log, log 50, log all, log clear
    - Hosts: hosts, hosts clear
    """
    cmd = raw.lower().strip()
    if not cmd:
        return ("unknown", "")

    parts = [p.strip(string.punctuation) for p in cmd.split()]
    parts = [p for p in parts if p]
    if not parts:
        return ("unknown", "")

    head = parts[0]

    # Exact phrase support
    if cmd == "disable alerts":
        return ("disable_alerts", None)

    # "log <arg>" support
    if head in ("log", "logs"):
        if len(parts) >= 2:
            return ("log", parts[1])
        return ("log", None)

    # "hosts <arg>" support
    if head == "hosts":
        if len(parts) >= 2:
            return ("hosts", parts[1])
        return ("hosts", None)

    # ping <target...>
    if head == "ping":
        if len(parts) == 1:
            return ("ping", None)
        return ("ping", " ".join(parts[1:]).strip())

    # Direct action aliases (single-word commands)
    if head in ACTION_SYNONYMS:
        return (ACTION_SYNONYMS[head], None)

    # Movement: "north" / "n"
    if head in DIRECTION_SYNONYMS:
        return ("move", DIRECTION_SYNONYMS[head])

    # Movement: "go <dir>" / "move <dir>"
    if head in ("go", "move") and len(parts) >= 2:
        maybe_dir = parts[1]
        if maybe_dir in DIRECTION_SYNONYMS:
            return ("move", DIRECTION_SYNONYMS[maybe_dir])
        return ("unknown", cmd)

    # Get: "get <item...>"
    if head == "get":
        if len(parts) == 1:
            return ("get", "")
        item_name = " ".join(parts[1:]).strip()
        return ("get", item_name)

    return ("unknown", cmd)


# -----------------------------
# OOP Model
# -----------------------------
@dataclass
class DetectionMeter:
    """
    Detection/Heat meter (0..100).
    Higher = more heat (worse).
    Start at 100 (hot), reduce it through progress.
    """

    value: int = 100

    def add(self, amount: int) -> None:
        self.value = max(0, min(100, self.value + amount))

    def reduce(self, amount: int) -> None:
        self.add(-amount)

    def label(self) -> str:
        if self.value >= 85:
            return "HIGH"
        if self.value >= 60:
            return "ELEVATED"
        if self.value >= 30:
            return "GUARDED"
        return "LOW"


@dataclass
class Player:
    name: str = "Operator"
    score: int = 0
    turns: int = 0

    inventory: set[str] = field(default_factory=set)
    alerts_disabled: bool = False
    has_network_map: bool = False
    detection: DetectionMeter = field(default_factory=DetectionMeter)

    # Discovered hosts: host -> ip
    discovered_hosts: dict[str, str] = field(default_factory=dict)

    def tick_turn(self) -> None:
        self.turns += 1

    def add_item(self, item: str) -> None:
        self.inventory.add(item)
        if item == "network map":
            self.has_network_map = True

    def add_score(self, points: int, reason: str = "") -> None:
        self.score += points
        if reason:
            sign = "+" if points >= 0 else ""
            print(f"Score {sign}{points}: {reason} (Total: {self.score})")

    def has_all_required(self, required: set[str]) -> bool:
        return required.issubset(self.inventory)


@dataclass
class Room:
    key: str
    name: str
    description: str
    exits: dict[str, str]
    item: Optional[str] = None
    obtain_method: str = "take"  # 'take' | 'exploit' | 'dump'

    # Added map_label so each room stores its own short map name.
    # This is more object-oriented than keeping the labels in a separate dictionary.
    map_label: str = ""

    def visible_item(self, player: Player) -> Optional[str]:
        if self.item and self.item not in player.inventory:
            return self.item
        return None

    def can_leave(self, player: Player, exempt_rooms: set[str]) -> tuple[bool, str]:
        # Exempt rooms do NOT force item pickup before leaving.
        if self.name in exempt_rooms and self.name != "Monitor Server":
            return True, ""

        # Special rule: can't leave Monitor Server until alerts disabled.
        if self.name == "Monitor Server" and not player.alerts_disabled:
            return False, "Disable alerts before leaving."

        # Only force pickup for take-based rooms
        if self.obtain_method == "take" and self.item and self.item not in player.inventory:
            return (
                False,
                f"You must collect '{self.item}' before leaving. Type: take (or get {self.item}).",
            )

        return True, ""


class Game:
    def __init__(self) -> None:
        self.rng = random.Random()
        self.player = Player()
        self.rooms = self._build_rooms()
        self.current_key = "jump_box"
        self.game_over = False

        # In-game session log (memory only)
        self.session_log: list[str] = []
        self.log_event("=== NEW SESSION START ===")
        self.log_event(f"CLI_DEMO_ENABLED={CLI_DEMO_ENABLED}")

    def _build_rooms(self) -> dict[str, Room]:
        return {
            "help_desk": Room(
                key="help_desk",
                name="Help Desk System",
                description="A low-privilege system containing support credentials.",
                exits={"east": "network_segment", "south": "file_server"},
                item="low-priv credentials",
                obtain_method="take",
                map_label="HELP",
            ),
            "network_segment": Room(
                key="network_segment",
                name="Network Segment",
                description="Core routing infrastructure. You see a detailed network map.",
                exits={"west": "help_desk", "east": "monitor_server", "south": "jump_box"},
                item="network map",
                obtain_method="take",
                map_label="NET",
            ),
            "monitor_server": Room(
                key="monitor_server",
                name="Monitor Server",
                description="Central monitoring system. Alerts are currently active.",
                exits={"west": "network_segment", "south": "user_workstation"},
                item="Kerberos ticket",
                obtain_method="dump",
                map_label="MON",
            ),
            "jump_box": Room(
                key="jump_box",
                name="Jump Box",
                description="A hardened system used to pivot into the internal network.",
                exits={"north": "network_segment", "east": "user_workstation", "south": "web_app_server"},
                item=None,
                map_label="JUMP",
            ),
            "user_workstation": Room(
                key="user_workstation",
                name="User Workstation",
                description="An employee machine with cached credentials.",
                exits={"west": "jump_box", "north": "monitor_server"},
                item="local admin hash",
                obtain_method="take",
                map_label="USER",
            ),
            "file_server": Room(
                key="file_server",
                name="File Server",
                description="Shared storage containing sensitive files.",
                exits={"north": "help_desk", "east": "web_app_server"},
                item="password dump",
                obtain_method="dump",
                map_label="FILE",
            ),
            "web_app_server": Room(
                key="web_app_server",
                name="Web App Server",
                description="Public-facing application server vulnerable to injection.",
                exits={"west": "file_server", "north": "jump_box", "south": "domain_controller"},
                item="SQL injection payload",
                obtain_method="exploit",
                map_label="WEB",
            ),
            "domain_controller": Room(
                key="domain_controller",
                name="Domain Controller",
                description="The core of the domain. Blue Team detection is active.",
                exits={"north": "web_app_server"},
                item=None,
                map_label="DC",
            ),
        }

    @property
    def current_room(self) -> Room:
        return self.rooms[self.current_key]

    # -----------------------------
    # In-game session log (memory only)
    # -----------------------------
    def log_event(self, message: str) -> None:
        ts = time.strftime("%H:%M:%S")
        self.session_log.append(f"[{ts}] {message}")

    def show_log(self, arg: Optional[str]) -> None:
        """
        Show session log.
        - log           -> last 15
        - log 50        -> last 50 (max 500)
        - log all       -> show all
        - log clear     -> clear log
        """
        if arg == "clear":
            self.session_log.clear()
            print("✅ Session log cleared.")
            self.log_event("Session log cleared.")
            return

        if arg == "all":
            to_show = self.session_log
        else:
            limit = 15
            if arg and arg.isdigit():
                limit = max(1, min(500, int(arg)))
            to_show = self.session_log[-limit:]

        if not to_show:
            print("(Session log empty)")
            return

        print("\n=== SESSION LOG ===")
        for line in to_show:
            print(line)
        print("===================\n")

    # -----------------------------
    # Host discovery (memory only)
    # -----------------------------
    def discover_host(self, host: str, ip: str, method: str) -> None:
        host = host.strip()
        ip = ip.strip()
        if not host or not ip:
            return

        prior = self.player.discovered_hosts.get(host)
        self.player.discovered_hosts[host] = ip

        if prior is None:
            self.log_event(f"DISCOVERY: {host} ({ip}) via {method}")
        elif prior != ip:
            self.log_event(f"DISCOVERY UPDATE: {host} {prior} -> {ip} via {method}")

    def show_hosts(self, arg: Optional[str]) -> None:
        """
        - hosts         -> show discovered hosts
        - hosts clear   -> clear list
        """
        if arg == "clear":
            self.player.discovered_hosts.clear()
            print("✅ Discovered host list cleared.")
            self.log_event("HOSTS cleared")
            return

        if not self.player.discovered_hosts:
            print("(No hosts discovered yet)")
            print("Tip: run 'scan' or 'ping <host>' to discover hosts.\n")
            return

        print("\n=== DISCOVERED HOSTS ===")
        for host in sorted(self.player.discovered_hosts.keys(), key=str.lower):
            ip = self.player.discovered_hosts[host]
            print(f"- {host:10s}  {ip}")
        print("========================\n")

    # -----------------------------
    # Paging helpers
    # -----------------------------
    def pause(self, prompt: str = "Press Enter to continue...") -> None:
        input(prompt)

    def print_block_paged(self, text: str, lines_per_page: int = 10) -> None:
        lines = text.splitlines()
        for i in range(0, len(lines), lines_per_page):
            chunk = lines[i : i + lines_per_page]
            print("\n".join(chunk))
            if i + lines_per_page < len(lines):
                self.pause()

    # -----------------------------
    # CLI Orchestration Demo (cross-platform, simulation only)
    # -----------------------------
    def run_shell_demo(self, label: str, command_text: str) -> None:
        """
        Cross-platform demo:
        - Uses current Python interpreter to print the simulated command text.
        - Does NOT execute real tools.
        - Always safe and works on Windows/macOS/Linux.
        """
        self.log_event(f"CLI/{label}: {command_text}")

        print(f"\n--- CLI Orchestration Demo ({label}) ---")
        try:
            result = subprocess.run(
                [sys.executable, "-c", f"print({command_text!r})"],
                capture_output=True,
                text=True,
                check=False,
            )
            out = (result.stdout or "").strip()
            print(out if out else "(no output)")
        except Exception as e:
            print(f"(CLI demo unavailable: {e})")
            self.log_event(f"CLI/{label} unavailable: {e}")
        print("--------------------------------------\n")

    # -----------------------------
    # UI
    # -----------------------------
    def show_help(self) -> None:
        print(
            """
Commands:
Movement:
- north / south / east / west
- n / s / e / w
- go <direction> / move <direction>

Actions:
- take            (pickup item in take-based rooms)
- get <item>      (same as take, but validates name)
- scan            (simulated scan output; adds a little noise)
- ping <host>     (simulated Linux-style ping; adds a little noise)
- exploit         (Web App Server only; adds noise)
- dump            (File Server / Monitor Server; adds noise)
- disable alerts  (Monitor Server only; BIG detection reduction)

Info:
- inventory
- detection
- map
- hosts          (show discovered hosts)
- hosts clear    (clear discovered hosts)
- log            (show last 15)
- log 50         (show last 50)
- log all        (show all)
- log clear      (clear log)
- help
- quit
"""
        )

    def print_startup_instructions(self) -> None:
        print("Welcome to the Network Penetration Simulation.")
        print("Objective: collect required artifacts and compromise the Domain Controller.")
        print("Scoring: faster completion = higher score.\n")

    def print_how_to_play(self) -> None:
        print("\n=== HOW TO PLAY ===")
        print("Scenario:")
        print("  You are a red team operator in a simulated corporate network (authorized test).")
        print("  Your mission is to complete the full chain and compromise the Domain Controller (DC).")
        print()

        print("Win condition:")
        print("  1) Collect ALL required artifacts (6 total).")
        print("  2) Enter the DC with LOW ENOUGH detection (heat) to avoid being flagged.")
        print()

        print("Detection (Heat) meter 0–100:")
        print("  - You START at 100/100 (HIGH heat).")
        print("  - The goal is to push detection DOWN through progress.")
        print("  - Movement/scan/exploit/dump/ping add small noise (can raise detection slightly).")
        print("  - Collecting artifacts and disabling alerts reduces detection significantly.")
        print()

        print("How you obtain each artifact (IMPORTANT):")
        print("  - Help Desk System:      take   -> low-priv credentials")
        print("  - Network Segment:       take   -> network map")
        print("  - User Workstation:      take   -> local admin hash")
        print("  - Web App Server:        exploit -> SQL injection payload (requires low-priv creds)")
        print("  - File Server:           dump   -> password dump (requires local admin hash)")
        print("  - Monitor Server:        disable alerts THEN dump -> Kerberos ticket")
        print()

        print("Discovery:")
        print("  - 'scan' and 'ping' add hosts to your in-memory discovered host list.")
        print("  - Use 'hosts' to view and 'hosts clear' to reset.")
        print()

        print("Score + speed:")
        print("  - You earn points for artifacts and objectives.")
        print("  - Every command = 1 TURN.")
        print("  - On victory, you get a speed bonus if you finish under the target turn count.")
        print()

        if CLI_DEMO_ENABLED:
            print("CLI demo mode: ENABLED (scan/ping/exploit/dump show simulated commands)")
        else:
            print("CLI demo mode: DISABLED (story mode)")

        print("\nTip: Type 'log' anytime to see your session activity history.\n")
        self.pause("Press Enter to view the recon/vulnerability summary...")

    def pre_engagement_brief(self) -> None:
        print("\n=== PRE-ENGAGEMENT RECON BRIEF ===")
        time.sleep(0.15)
        print("[+] Initial network scan completed")
        print("[+] Internal routing path confirmed via jump box")
        print("[!] Monitoring system detected (alerts likely active)")
        print("[!] Web application exposure identified (possible injection point)")
        print("[!] Credential reuse suspected on internal hosts)")
        print("[!] High-value target detected: Domain Controller (heavy monitoring)")
        print("Proceed with caution.")
        print("=================================\n")

        summary = """=== SIMULATED VULNERABILITY SUMMARY ===
Scope: Internal corporate segment (authorized test)
Method: Simulated discovery + service fingerprinting + rule-based findings

- Host: HELPDESK (Help Desk System)  (10.10.10.11)
  Services: 445/tcp SMB, 3389/tcp RDP
  Severity: MEDIUM  |  Finding: Credential Exposure / Reuse Signal
  Detail:   Support artifacts suggest reused/default credentials and weak internal
           hygiene.
  Intel:    Likely contains: low-priv credentials (take).

- Host: NET-CORE (Network Segment)  (10.10.10.20)
  Services: 161/udp SNMP, 22/tcp SSH
  Severity: LOW  |  Finding: Infrastructure Intel Available
  Detail:   Management-plane access suggests routing/diagram intel is reachable.
  Intel:    Likely contains: network map (take) to reduce operational risk.

- Host: MON-01 (Monitor Server)  (10.10.10.30)
  Services: 5601/tcp Dashboard, 9200/tcp Telemetry API
  Severity: HIGH  |  Finding: Active Monitoring / Alerting
  Detail:   Central alerting/event-forwarding present; noisy actions increase
           detection.
  Intel:    Disable alerts before leaving; later extraction possible (dump).

- Host: WS-041 (User Workstation)  (10.10.10.41)
  Services: 445/tcp SMB, 135/tcp MSRPC
  Severity: MEDIUM  |  Finding: Credential Residue Likely
  Detail:   Workstation patterns consistent with cached credentials/session
           artifacts.
  Intel:    Likely contains: local admin hash (take).

- Host: FILE-01 (File Server)  (10.10.10.55)
  Services: 445/tcp SMB Shares, 5985/tcp WinRM
  Severity: HIGH  |  Finding: Sensitive Share / Credential Archive Risk
  Detail:   Shared storage likely contains exported configs/password archives.
  Intel:    Extraction requires privilege (dump after admin hash).

- Host: WEBAPP (Web App Server)  (10.10.10.80)
  Services: 80/tcp HTTP, 443/tcp HTTPS
  Severity: HIGH  |  Finding: Input Validation Weakness Indicator
  Detail:   Request patterns suggest injection exposure in app flows.
  Intel:    Use exploit to obtain SQL injection payload artifact.

- Host: DC-01 (Domain Controller)  (10.10.10.10)
  Services: 88/tcp Kerberos, 389/tcp LDAP, 445/tcp SMB
  Severity: CRITICAL  |  Finding: Hardened High-Value Target
  Detail:   Heavy monitoring + strict access controls; compromise requires full
           chain.
  Intel:    Enter only after collecting all required artifacts and lowering detection.
"""
        self.print_block_paged(summary, lines_per_page=10)
        print("\n=== END VULNERABILITY SUMMARY ===\n")
        self.pause("Press Enter to begin...")

    # -----------------------------
    # Improved map rendering
    # -----------------------------
    def show_map(self) -> None:
        """
        Render a cleaner network map using a helper function.

        Why this is better:
        - The room label comes from the Room object itself (map_label).
        - The current room marker is handled in one place.
        - The layout is easier to maintain and explain.
        - This was adapted from instructor feedback about improving map usability.
        """

        def m(room_key: str) -> str:
            """
            Render one room box.
            The current room is marked with * on both sides of the short label.
            Example:
                [*JUMP*]
                [ HELP ]
            """
            room = self.rooms[room_key]
            mark = "*" if room_key == self.current_key else " "
            label = room.map_label.center(4)
            return f"[{mark}{label}{mark}]"

        print("\n=== NETWORK MAP ===")
        print(
            f"""
{m("help_desk")} ⇄ {m("network_segment")} ⇄ {m("monitor_server")}
      ⇅               ⇅               ⇅
{m("file_server")}     ⇄ {m("jump_box")} ⇄ {m("user_workstation")}
                        ⇅
                    {m("web_app_server")}
                        ⇅
                    {m("domain_controller")}

*ROOM* = you are here
"""
        )

    def show_room(self) -> None:
        room = self.current_room
        p = self.player

        print(f"\nYou are in the {room.name}.")
        print(f"Operator: {p.name} | Score: {p.score} | Turns: {p.turns}")

        inv = sorted(p.inventory) if p.inventory else []
        print(f"Inventory: {inv}")

        if room.name == "Monitor Server":
            print(
                "Central monitoring system. Alerts are offline."
                if p.alerts_disabled
                else "Central monitoring system. Alerts are currently active."
            )
        else:
            print(room.description)

        item = room.visible_item(p)
        if item:
            desc = ITEM_DESCRIPTIONS.get(item, "")
            how = room.obtain_method
            hint = "take" if how == "take" else how
            print(f"You see: {item}" + (f" — {desc}" if desc else ""))
            print(f"Acquisition: use '{hint}'")

        print(
            f"Detection: {p.detection.value}/100 ({p.detection.label()})"
            + (" — alerts disabled" if p.alerts_disabled else "")
            + (" — network map in use" if p.has_network_map else "")
        )

        exits = ", ".join(room.exits.keys()) if room.exits else "none"
        print(f"Available moves: {exits}")

    # -----------------------------
    # Detection mechanics
    # -----------------------------
    def add_noise(self, base: int) -> None:
        p = self.player
        amt = base

        if p.alerts_disabled:
            amt = max(0, int(amt * 0.5))

        if p.has_network_map:
            amt = max(0, int(amt * 0.8))

        p.detection.add(amt)

    def reduce_detection(self, amount: int, reason: str) -> None:
        before = self.player.detection.value
        self.player.detection.reduce(amount)
        after = self.player.detection.value
        print(f"🟢 Detection -{before - after}: {reason} (Now {after}/100)")
        self.log_event(f"DETECTION -{before - after}: {reason} -> {after}/100")

    # -----------------------------
    # Scoring / speed bonus
    # -----------------------------
    def apply_speed_bonus(self, victory: bool) -> None:
        if not victory:
            return
        turns = self.player.turns
        target = 22
        delta = max(0, target - turns)
        bonus = 25 + (delta * 6)
        self.player.add_score(bonus, f"Speed bonus (turns={turns}, target={target})")
        self.log_event(f"SPEED BONUS +{bonus} (turns={turns}, target={target})")

    # -----------------------------
    # Actions
    # -----------------------------
    def try_take_item(self, requested_item: Optional[str]) -> None:
        room = self.current_room
        p = self.player

        item = room.visible_item(p)
        if not item:
            print("Nothing to take here.")
            self.log_event(f"TAKE failed: no item in {room.name}")
            return

        if room.obtain_method != "take":
            print(f"You cannot take this directly. Required action: {room.obtain_method}")
            self.log_event(f"TAKE blocked: {room.name} requires {room.obtain_method}")
            return

        if requested_item is not None and requested_item != item:
            print(f"You can't get '{requested_item}' here.")
            self.log_event(
                f"GET failed: requested='{requested_item}' available='{item}' in {room.name}"
            )
            return

        self.add_noise(1)

        p.add_item(item)
        p.add_score(10, f"Collected artifact: {item}")
        self.log_event(f"ARTIFACT TAKE: {item} (+10 score) in {room.name}")

        self.reduce_detection(12, f"Artifact secured: {item}")
        print(f"You collected: {item}")

    # -----------------------------
    # Simulated ping (Linux-style)
    # -----------------------------
    def _is_ipv4(self, s: str) -> bool:
        s = s.strip()
        parts = s.split(".")
        if len(parts) != 4:
            return False
        for p in parts:
            if not p.isdigit():
                return False
            n = int(p)
            if n < 0 or n > 255:
                return False
        return True

    def ping_profile(
        self, target: str
    ) -> tuple[bool, int, int, str, Optional[str], Optional[str]]:
        """
        Returns:
          (reachable, loss_pct, rtt_ms, resolved_ip, discovered_host, discovered_ip)
        """
        room = self.current_room.name
        t_raw = target.strip()
        t = t_raw.lower()

        known_aliases: dict[str, tuple[str, str]] = {
            "jump": ("JUMP-01", "10.10.10.1"),
            "jumpbox": ("JUMP-01", "10.10.10.1"),
            "gateway": ("JUMP-01", "10.10.10.1"),
            "helpdesk": ("HELPDESK", "10.10.10.11"),
            "help": ("HELPDESK", "10.10.10.11"),
            "net": ("NET-CORE", "10.10.10.20"),
            "net-core": ("NET-CORE", "10.10.10.20"),
            "monitor": ("MON-01", "10.10.10.30"),
            "mon": ("MON-01", "10.10.10.30"),
            "ws": ("WS-041", "10.10.10.41"),
            "ws-041": ("WS-041", "10.10.10.41"),
            "file": ("FILE-01", "10.10.10.55"),
            "file-01": ("FILE-01", "10.10.10.55"),
            "web": ("WEBAPP", "10.10.10.80"),
            "webapp": ("WEBAPP", "10.10.10.80"),
            "dc": ("DC-01", "10.10.10.10"),
            "dc-01": ("DC-01", "10.10.10.10"),
        }

        discovered_host: Optional[str] = None
        discovered_ip: Optional[str] = None
        resolved_ip = "10.10.10.99"

        is_known = False
        if t in known_aliases:
            discovered_host, discovered_ip = known_aliases[t]
            resolved_ip = discovered_ip
            is_known = True
        elif self._is_ipv4(t_raw):
            resolved_ip = t_raw
            discovered_host, discovered_ip = t_raw, t_raw
            is_known = True

        # Strict visibility from Jump Box
        if room == "Jump Box":
            if t in ("gateway", "jump", "jumpbox") or t_raw == "10.10.10.1":
                return True, 0, 7, "10.10.10.1", "JUMP-01", "10.10.10.1"
            return False, 100, 0, resolved_ip, None, None

        # Base loss depends on intel / environment
        base_loss = 0 if self.player.has_network_map else 25

        # Alerts active in sensitive rooms -> likely filtering / drops
        if room in ("Monitor Server", "Domain Controller") and not self.player.alerts_disabled:
            base_loss = max(base_loss, 50)

        # High detection -> tighter controls
        det = self.player.detection.value
        if det >= 85:
            base_loss = max(base_loss, 50)
        elif det >= 60:
            base_loss = max(base_loss, 25)

        reachable = is_known
        rtt = 10 if self.player.has_network_map else 18
        return reachable, base_loss, rtt, resolved_ip, discovered_host, discovered_ip

    def simulate_ping_output_linux(
        self,
        target_label: str,
        resolved_ip: str,
        reachable: bool,
        loss_pct: int,
        rtt_ms: int,
        count: int = 4,
    ) -> str:
        """
        Linux-style ping output.
        """
        target_label = target_label.strip()
        resolved_ip = resolved_ip.strip()

        if not target_label:
            return "usage: ping <host>\n"

        lines: list[str] = []
        lines.append(f"PING {target_label} ({resolved_ip}) 56(84) bytes of data.")

        if not reachable:
            lines.append("")
            lines.append(f"--- {target_label} ping statistics ---")
            lines.append(f"{count} packets transmitted, 0 received, 100% packet loss, time {count*1000}ms")
            return "\n".join(lines) + "\n"

        received = count - round(count * (loss_pct / 100))
        received = max(1, min(count, received))
        lost = count - received
        loss_line = int((lost / count) * 100)

        times: list[float] = []
        for seq in range(1, received + 1):
            t_ms = float(rtt_ms + (seq - 1))
            times.append(t_ms)
            lines.append(f"64 bytes from {resolved_ip}: icmp_seq={seq} ttl=64 time={t_ms:.1f} ms")

        lines.append("")
        lines.append(f"--- {target_label} ping statistics ---")
        lines.append(
            f"{count} packets transmitted, {received} received, {loss_line}% packet loss, time {count*1000}ms"
        )

        t_min = min(times)
        t_max = max(times)
        t_avg = sum(times) / len(times)
        mdev = max(0.1, (t_max - t_min) / 2.0)
        lines.append(f"rtt min/avg/max/mdev = {t_min:.3f}/{t_avg:.3f}/{t_max:.3f}/{mdev:.3f} ms")

        return "\n".join(lines) + "\n"

    def cmd_ping(self, target: Optional[str]) -> None:
        if not target:
            print("Usage: ping <host>")
            self.log_event("PING failed: missing target")
            return

        self.add_noise(1)

        reachable, loss, rtt, resolved_ip, d_host, d_ip = self.ping_profile(target)

        if CLI_DEMO_ENABLED:
            self.run_shell_demo("ping", f"ping -c 4 {target} (simulated)")

        out = self.simulate_ping_output_linux(
            target_label=target,
            resolved_ip=resolved_ip,
            reachable=reachable,
            loss_pct=loss,
            rtt_ms=rtt,
            count=4,
        )

        print("\n=== SIMULATED PING OUTPUT ===")
        print(out.rstrip())
        print("============================\n")

        if reachable and d_host and d_ip:
            self.discover_host(d_host, d_ip, method="ping")
            print(f"[+] Discovered: {d_host} ({d_ip})\n")
        else:
            print("Note: ICMP may be blocked; lack of reply doesn’t prove the host is down.\n")

        self.log_event(
            f"PING: target={target} resolved={resolved_ip} reachable={reachable} loss={loss}% rtt~{rtt}ms in {self.current_room.name}"
        )

    def cmd_scan(self) -> None:
        self.add_noise(2)

        room = self.current_room.name
        host_map = {
            "Jump Box": ("10.10.10.1", "JUMP-01"),
            "Help Desk System": ("10.10.10.11", "HELPDESK"),
            "Network Segment": ("10.10.10.20", "NET-CORE"),
            "Monitor Server": ("10.10.10.30", "MON-01"),
            "User Workstation": ("10.10.10.41", "WS-041"),
            "File Server": ("10.10.10.55", "FILE-01"),
            "Web App Server": ("10.10.10.80", "WEBAPP"),
            "Domain Controller": ("10.10.10.10", "DC-01"),
        }
        hints = {
            "Help Desk System": "Finding: Credential exposure signal (take low-priv creds).",
            "Network Segment": "Finding: Routing intel present (take network map).",
            "Monitor Server": "Finding: Alerting active (disable alerts recommended).",
            "User Workstation": "Finding: Cached credential artifacts likely (take admin hash).",
            "File Server": "Finding: Sensitive shares may contain credential archives (dump).",
            "Web App Server": "Finding: Injection indicator observed (exploit).",
            "Domain Controller": "Finding: Hardened target (reduce detection before entry).",
            "Jump Box": "Finding: Pivot host confirmed.",
        }

        ip, host = host_map.get(room, ("10.10.10.99", "UNKNOWN"))

        if CLI_DEMO_ENABLED:
            self.run_shell_demo("scan", f"nmap {ip} (simulated)")

        print("\n=== SIMULATED SCAN OUTPUT ===")
        print(f"Target: {ip} ({host})")
        print("Host is up (simulated).")
        print(hints.get(room, "Finding: No additional intel."))
        print("=============================\n")

        if host != "UNKNOWN":
            self.discover_host(host, ip, method="scan")
            print(f"[+] Discovered: {host} ({ip})\n")

        self.log_event(f"SCAN: {host} ({ip}) in {room}")

    def cmd_exploit(self) -> None:
        room = self.current_room
        p = self.player

        if room.name != "Web App Server":
            print("Exploit attempt not applicable here.")
            self.log_event(f"EXPLOIT blocked: not applicable in {room.name}")
            return

        if "SQL injection payload" in p.inventory:
            print("You already extracted the SQL injection payload.")
            self.log_event("EXPLOIT skipped: SQL injection payload already owned")
            return

        if "low-priv credentials" not in p.inventory:
            print("Exploit blocked: you need low-priv credentials first (Help Desk System).")
            self.log_event("EXPLOIT blocked: missing low-priv credentials")
            return

        self.add_noise(4)

        if CLI_DEMO_ENABLED:
            self.run_shell_demo("exploit", "sqlmap -u http://10.10.10.80/login --batch (simulated)")

        print("\n[+] Exploit simulation: probing web input handling...")
        time.sleep(0.2)
        print("[+] Injection indicator confirmed (simulated).")
        time.sleep(0.2)
        print("[+] Extracting exploitation artifact...")
        time.sleep(0.2)

        p.add_item("SQL injection payload")
        p.add_score(25, "Successful exploitation (simulated)")
        self.log_event("ARTIFACT EXPLOIT: SQL injection payload (+25 score)")

        self.reduce_detection(15, "Web exploitation complete")
        print("✅ Collected: SQL injection payload")

    def cmd_dump(self) -> None:
        room = self.current_room
        p = self.player

        if room.name == "File Server":
            if "password dump" in p.inventory:
                print("You already extracted the password dump.")
                self.log_event("DUMP skipped: password dump already owned")
                return

            if "local admin hash" not in p.inventory:
                print("Dump blocked: you need the local admin hash first (User Workstation).")
                self.log_event("DUMP blocked: missing local admin hash for File Server")
                return

            self.add_noise(3)

            if CLI_DEMO_ENABLED:
                self.run_shell_demo("dump", "secretsdump.py DOMAIN/user@10.10.10.55 (simulated)")

            print("\n[+] Dump simulation: enumerating shares...")
            time.sleep(0.2)
            print("[+] Privileged access established (simulated).")
            time.sleep(0.2)
            print("[+] Extracting credential archive...")
            time.sleep(0.2)

            p.add_item("password dump")
            p.add_score(30, "Extracted credential archive (simulated)")
            self.log_event("ARTIFACT DUMP: password dump (+30 score)")

            self.reduce_detection(18, "Credential archive secured")
            print("✅ Collected: password dump")
            return

        if room.name == "Monitor Server":
            if "Kerberos ticket" in p.inventory:
                print("You already extracted the Kerberos ticket.")
                self.log_event("DUMP skipped: Kerberos ticket already owned")
                return

            if not p.alerts_disabled:
                print("Dump blocked: alerts are active. Disable alerts first.")
                self.log_event("DUMP blocked: alerts active on Monitor Server")
                return

            self.add_noise(2)

            if CLI_DEMO_ENABLED:
                self.run_shell_demo("dump", "ticket-extract --source telemetry-cache (simulated)")

            print("\n[+] Dump simulation: pulling auth artifacts from telemetry cache...")
            time.sleep(0.2)
            print("[+] Token material located (simulated).")
            time.sleep(0.2)

            p.add_item("Kerberos ticket")
            p.add_score(40, "Extracted Kerberos ticket (simulated)")
            self.log_event("ARTIFACT DUMP: Kerberos ticket (+40 score)")

            self.reduce_detection(22, "Golden ticket obtained")
            print("✅ Collected: Kerberos ticket")
            return

        print("Dump operation not applicable here.")
        self.log_event(f"DUMP blocked: not applicable in {room.name}")

    def disable_alerts(self) -> None:
        p = self.player
        if self.current_room.name != "Monitor Server":
            print("No alerts here.")
            self.log_event(
                f"DISABLE ALERTS blocked: not in Monitor Server (in {self.current_room.name})"
            )
            return

        if p.alerts_disabled:
            print("Alerts are already disabled.")
            self.log_event("DISABLE ALERTS skipped: already disabled")
            return

        self.add_noise(3)
        p.alerts_disabled = True
        p.add_score(20, "Disabled monitoring alerts")
        self.log_event("ALERTS DISABLED (+20 score)")

        self.reduce_detection(25, "Alerting neutralized")
        print("✅ Alerts disabled. You can now leave the Monitor Server safely.")

    def move(self, direction: str) -> None:
        room = self.current_room
        p = self.player

        allowed, msg = room.can_leave(p, EXEMPT_ROOMS)
        if not allowed:
            print(msg)
            self.log_event(f"MOVE blocked: {msg} (in {room.name})")
            return

        if direction not in room.exits:
            print("You cannot go that way.")
            self.log_event(f"MOVE blocked: no exit '{direction}' from {room.name}")
            return

        move_noise = 2 if not p.has_network_map else 1
        self.add_noise(move_noise)

        prev_name = room.name
        self.current_key = room.exits[direction]
        self.log_event(
            f"MOVE {direction}: {prev_name} -> {self.current_room.name} (noise +{move_noise})"
        )

        if self.current_room.name == "Domain Controller":
            self.resolve_domain_controller()

    # -----------------------------
    # Endgame
    # -----------------------------
    def resolve_domain_controller(self) -> None:
        print("\nYou step into the Domain Controller...")

        self.show_room()
        self.show_map()

        if not self.player.has_all_required(REQUIRED_ITEMS):
            missing = sorted(REQUIRED_ITEMS - self.player.inventory)
            print("\n🚨 You entered the Domain Controller without all required artifacts.")
            print("Missing:", ", ".join(missing))
            self.log_event(f"END FAIL: missing artifacts: {', '.join(missing)}")
            self.end_game(False)
            return

        threshold = 40 if self.player.alerts_disabled else 55
        if self.player.detection.value > threshold:
            self.player.add_score(-25, "Flagged at DC entry (detection too high)")
            print("\n⚠️  You were flagged entering the DC.")
            print(f"Required detection <= {threshold}, but you had {self.player.detection.value}.")
            self.log_event(
                f"END FAIL: flagged at DC (det={self.player.detection.value}, threshold={threshold})"
            )
            self.end_game(False)
            return

        print("\n✅ Access granted. Domain Controller compromised.")
        self.player.add_score(100, "Domain Controller compromised")
        self.log_event("END WIN: Domain Controller compromised (+100 score)")
        self.end_game(True)

    def end_game(self, victory: bool) -> None:
        self.apply_speed_bonus(victory)

        print("\nMISSION ACCOMPLISHED" if victory else "\nMISSION FAILED")
        print(f"Operator: {self.player.name}")
        print(f"Final Score: {self.player.score}")
        print(f"Turns: {self.player.turns}")
        print(f"Detection: {self.player.detection.value}/100 ({self.player.detection.label()})")
        print("Game over.")

        self.log_event(
            f"=== SESSION END === victory={victory} score={self.player.score} turns={self.player.turns} det={self.player.detection.value}/100"
        )
        self.game_over = True

    # -----------------------------
    # Main loop
    # -----------------------------
    def run(self) -> None:
        self.print_startup_instructions()
        self.show_help()

        name = input("Enter operator name: ").strip()
        if name:
            self.player.name = name
        self.log_event(f"OPERATOR: {self.player.name}")

        self.print_how_to_play()
        self.pre_engagement_brief()

        while not self.game_over:
            self.show_room()
            self.show_map()

            raw = input("\nCommand: ")
            self.player.tick_turn()

            self.log_event(
                f"TURN {self.player.turns}: '{raw}' in {self.current_room.name} | "
                f"score={self.player.score} det={self.player.detection.value}/100"
            )

            action, arg = normalize_command(raw)

            if action == "log":
                self.show_log(arg)
                continue

            if action == "hosts":
                self.show_hosts(arg)
                continue

            if action == "ping":
                self.cmd_ping(arg)
                continue

            if action == "get":
                if not arg:
                    print("Usage: get <item name>")
                else:
                    self.try_take_item(arg)
                continue

            if action == "take":
                self.try_take_item(None)
                continue

            if action == "scan":
                self.cmd_scan()
                continue

            if action == "exploit":
                self.cmd_exploit()
                continue

            if action == "dump":
                self.cmd_dump()
                continue

            if action == "disable_alerts":
                self.disable_alerts()
                continue

            if action == "inventory":
                inv = sorted(self.player.inventory) if self.player.inventory else []
                print("Inventory:", inv if inv else "Empty")
                continue

            if action == "detection":
                d = self.player.detection
                print(f"Detection: {d.value}/100 ({d.label()})")
                continue

            if action == "map":
                self.show_map()
                continue

            if action == "help":
                self.show_help()
                continue

            if action == "quit":
                print("Session terminated.")
                self.log_event("QUIT: user terminated session")
                break

            if action == "move":
                self.move(arg or "")
                continue

            print("Unknown command. Type 'help' to see available commands.")


def main() -> None:
    Game().run()


if __name__ == "__main__":
    main()
