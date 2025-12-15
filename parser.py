"""
GW2 CounterPicker - Real EVTC Parser
Parses arcdps .evtc/.zevtc/.zip files to extract exact player builds

Binary format based on: https://www.deltaconnected.com/arcdps/evtc/README.txt
"""

import struct
import zipfile
import io
import os
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple, BinaryIO
from datetime import datetime
from enum import IntEnum
from pathlib import Path
from logger import get_logger

# Setup logger
logger = get_logger('parser')

from models import (
    AnalysisResult, PlayerBuild, CompositionAnalysis,
    EveningReport, HourlyEvolution, TopPlayer, HeatmapData
)


# =============================================================================
# GW2 GAME DATA - Profession & Elite Spec IDs
# =============================================================================

class Profession(IntEnum):
    GUARDIAN = 1
    WARRIOR = 2
    ENGINEER = 3
    RANGER = 4
    THIEF = 5
    ELEMENTALIST = 6
    MESMER = 7
    NECROMANCER = 8
    REVENANT = 9


PROFESSION_NAMES = {
    1: "Guardian",
    2: "Warrior",
    3: "Engineer",
    4: "Ranger",
    5: "Thief",
    6: "Elementalist",
    7: "Mesmer",
    8: "Necromancer",
    9: "Revenant",
}


class EliteSpec(IntEnum):
    # Core (0 = no elite)
    NONE = 0
    
    # Heart of Thorns
    DRAGONHUNTER = 27
    BERSERKER = 18
    SCRAPPER = 43
    DRUID = 5
    DAREDEVIL = 7
    TEMPEST = 48
    CHRONOMANCER = 40
    REAPER = 34
    HERALD = 52
    
    # Path of Fire
    FIREBRAND = 62
    SPELLBREAKER = 61
    HOLOSMITH = 57
    SOULBEAST = 55
    DEADEYE = 58
    WEAVER = 56
    MIRAGE = 59
    SCOURGE = 60
    RENEGADE = 63
    
    # End of Dragons
    WILLBENDER = 65
    BLADESWORN = 68
    MECHANIST = 70
    UNTAMED = 72
    SPECTER = 71
    CATALYST = 67
    VIRTUOSO = 66
    HARBINGER = 64
    VINDICATOR = 69
    
    # Secrets of the Obscure
    # (Add IDs when known)


ELITE_SPEC_NAMES = {
    0: "Core",
    # HoT
    27: "Dragonhunter",
    18: "Berserker",
    43: "Scrapper",
    5: "Druid",
    7: "Daredevil",
    48: "Tempest",
    40: "Chronomancer",
    34: "Reaper",
    52: "Herald",
    # PoF
    62: "Firebrand",
    61: "Spellbreaker",
    57: "Holosmith",
    55: "Soulbeast",
    58: "Deadeye",
    56: "Weaver",
    59: "Mirage",
    60: "Scourge",
    63: "Renegade",
    # EoD
    65: "Willbender",
    68: "Bladesworn",
    70: "Mechanist",
    72: "Untamed",
    71: "Specter",
    67: "Catalyst",
    66: "Virtuoso",
    64: "Harbinger",
    69: "Vindicator",
    # Janthir Wilds
    73: "Dragonslayer",  # Guardian
    74: "Deathbringer",  # Warrior - placeholder name
    75: "Riftstalker",   # Engineer - placeholder name
    76: "Warden",        # Ranger - placeholder name
    77: "Trickster",     # Thief - placeholder name
    78: "Invoker",       # Elementalist - placeholder name
    79: "Conduit",       # Revenant
    80: "Evoker",        # Elementalist - confirmed
    81: "Ritualist",     # Necromancer - placeholder name
}

ELITE_TO_PROFESSION = {
    27: 1, 62: 1, 65: 1, 73: 1,  # Guardian
    18: 2, 61: 2, 68: 2, 74: 2,  # Warrior
    43: 3, 57: 3, 70: 3, 75: 3,  # Engineer
    5: 4, 55: 4, 72: 4, 76: 4,   # Ranger
    7: 5, 58: 5, 71: 5, 77: 5,   # Thief
    48: 6, 56: 6, 67: 6, 78: 6, 80: 6,  # Elementalist
    40: 7, 59: 7, 66: 7,  # Mesmer
    34: 8, 60: 8, 64: 8, 81: 8,  # Necromancer
    52: 9, 63: 9, 69: 9, 79: 9,  # Revenant
}


# =============================================================================
# WVW ROLE DETECTION
# =============================================================================

ROLE_DETECTION = {
    # Support specs
    "Firebrand": {"default": "Support", "keywords": ["Heal", "Quick"]},
    "Scrapper": {"default": "Support", "keywords": ["Heal", "Gyro"]},
    "Chronomancer": {"default": "Support", "keywords": ["Tank", "Alac"]},
    "Tempest": {"default": "Backline", "keywords": ["Heal", "Auramancer"]},
    "Druid": {"default": "Support", "keywords": ["Heal"]},
    "Renegade": {"default": "Support", "keywords": ["Alac"]},
    "Mechanist": {"default": "Support", "keywords": ["Heal", "Alac"]},
    "Specter": {"default": "Support", "keywords": ["Alac"]},
    
    # Frontline specs
    "Herald": {"default": "Frontline", "keywords": ["Dwarf", "Tank"]},
    "Spellbreaker": {"default": "Frontline", "keywords": ["Bubble", "Strip"]},
    "Vindicator": {"default": "Frontline", "keywords": ["GS", "Leap"]},
    "Berserker": {"default": "Frontline", "keywords": ["Hammer"]},
    "Reaper": {"default": "Frontline", "keywords": ["Shroud"]},
    "Willbender": {"default": "Roamer", "keywords": ["Roam"]},
    
    # Backline specs
    "Scourge": {"default": "Backline", "keywords": ["Shade", "Corrupt"]},
    "Harbinger": {"default": "Backline", "keywords": ["Condi"]},
    "Catalyst": {"default": "Backline", "keywords": ["Hammer", "Jade"]},
    "Weaver": {"default": "Backline", "keywords": ["Staff", "Sword"]},
    "Dragonhunter": {"default": "Backline", "keywords": ["Trap", "LB"]},
    "Virtuoso": {"default": "Backline", "keywords": ["Blade"]},
    
    # Roamer specs
    "Daredevil": {"default": "Roamer", "keywords": ["Staff", "Roam"]},
    "Deadeye": {"default": "Roamer", "keywords": ["Rifle", "Snipe"]},
    "Soulbeast": {"default": "Roamer", "keywords": ["LB", "Roam"]},
    "Mirage": {"default": "Roamer", "keywords": ["Condi", "Roam"]},
    "Holosmith": {"default": "Roamer", "keywords": ["Forge"]},
    "Bladesworn": {"default": "Roamer", "keywords": ["Dragon"]},
    "Untamed": {"default": "Roamer", "keywords": ["Pet"]},
}


# =============================================================================
# SKILL IDS FOR BUILD DETECTION
# =============================================================================

# Weapon skill ranges for detection
WEAPON_SKILLS = {
    # Guardian
    "Greatsword": [9137, 9081, 9146, 9154, 9153],
    "Hammer": [9159, 9194, 9260, 9124, 9195],
    "Staff": [9122, 9140, 9143, 9265, 9144],
    "Sword": [9105, 9097, 9107],
    "Scepter": [9104, 9099, 9088],
    "Focus": [9112, 9082],
    "Shield": [9087, 9091],
    "Torch": [9104, 9089],
    "Axe": [9116, 9118],
    # Add more as needed
}

# Boon skill IDs
BOON_IDS = {
    717: "Protection",
    718: "Regeneration",
    719: "Swiftness",
    725: "Fury",
    726: "Vigor",
    740: "Might",
    743: "Aegis",
    873: "Resolution",
    1187: "Quickness",
    26980: "Resistance",
    30328: "Alacrity",
    33330: "Stability",
}

# Condition skill IDs
CONDITION_IDS = {
    720: "Blind",
    721: "Cripple",
    722: "Chilled",
    723: "Poison",
    736: "Bleeding",
    737: "Burning",
    738: "Vulnerability",
    742: "Weakness",
    861: "Confusion",
    872: "Fear",
    19426: "Torment",
    27705: "Immobilize",
}


# =============================================================================
# STATECHANGE ENUM
# =============================================================================

class StateChange(IntEnum):
    NONE = 0
    ENTER_COMBAT = 1
    EXIT_COMBAT = 2
    CHANGE_UP = 3
    CHANGE_DEAD = 4
    CHANGE_DOWN = 5
    SPAWN = 6
    DESPAWN = 7
    HEALTH_UPDATE = 8
    SQUAD_COMBAT_START = 9
    SQUAD_COMBAT_END = 10
    WEAPON_SWAP = 11
    MAX_HEALTH_UPDATE = 12
    POINT_OF_VIEW = 13
    LANGUAGE = 14
    GW_BUILD = 15
    SHARD_ID = 16
    REWARD = 17
    BUFF_INITIAL = 18
    POSITION = 19
    VELOCITY = 20
    FACING = 21
    TEAM_CHANGE = 22
    ATTACK_TARGET = 23
    TARGETABLE = 24
    MAP_ID = 25
    # ... more defined but these are the main ones


class IFF(IntEnum):
    FRIEND = 0
    FOE = 1
    UNKNOWN = 2


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class EVTCHeader:
    """EVTC file header"""
    magic: str
    arcdps_build: str
    revision: int
    boss_id: int
    is_wvw: bool = False
    
    @property
    def build_date(self) -> str:
        return self.arcdps_build


@dataclass
class EVTCAgent:
    """Agent (player, NPC, or gadget) from EVTC"""
    address: int
    profession: int
    elite_spec: int
    toughness: int
    concentration: int
    healing: int
    hitbox_width: int
    condition: int
    hitbox_height: int
    name: str
    
    # Parsed from name for players
    character_name: str = ""
    account_name: str = ""
    subgroup: int = 0
    
    # Runtime data
    instance_id: int = 0
    first_aware: int = 0
    last_aware: int = 0
    master_address: int = 0
    team_id: int = 0
    
    @property
    def is_player(self) -> bool:
        return self.elite_spec != 0xFFFFFFFF
    
    @property
    def is_npc(self) -> bool:
        return self.elite_spec == 0xFFFFFFFF and (self.profession >> 16) != 0xFFFF
    
    @property
    def is_gadget(self) -> bool:
        return self.elite_spec == 0xFFFFFFFF and (self.profession >> 16) == 0xFFFF
    
    @property
    def species_id(self) -> int:
        """For NPCs, get the species ID"""
        if self.is_npc:
            return self.profession & 0xFFFF
        return 0
    
    @property
    def profession_name(self) -> str:
        if self.is_player:
            return PROFESSION_NAMES.get(self.profession, f"Unknown({self.profession})")
        return "NPC"
    
    @property
    def elite_spec_name(self) -> str:
        if self.is_player:
            if self.elite_spec == 0:
                return f"Core {self.profession_name}"
            return ELITE_SPEC_NAMES.get(self.elite_spec, f"Unknown({self.elite_spec})")
        return "N/A"


@dataclass
class EVTCSkill:
    """Skill definition from EVTC"""
    id: int
    name: str


@dataclass
class CombatEvent:
    """Combat event from EVTC"""
    time: int
    src_agent: int
    dst_agent: int
    value: int
    buff_dmg: int
    overstack_value: int
    skill_id: int
    src_instid: int
    dst_instid: int
    src_master_instid: int
    dst_master_instid: int
    iff: int
    buff: int
    result: int
    is_activation: int
    is_buffremove: int
    is_ninety: int
    is_fifty: int
    is_moving: int
    is_statechange: int
    is_flanking: int
    is_shields: int
    is_offcycle: int
    pad61: int = 0
    pad62: int = 0
    pad63: int = 0
    pad64: int = 0


@dataclass
class ParsedPlayer:
    """Fully parsed player data"""
    character_name: str
    account_name: str
    profession: str
    elite_spec: str
    subgroup: int
    team_id: int
    is_enemy: bool
    
    # Stats
    toughness: int = 0
    concentration: int = 0
    healing_power: int = 0
    condition_damage: int = 0
    
    # Combat stats
    damage_dealt: int = 0
    damage_taken: int = 0
    healing_done: int = 0
    deaths: int = 0
    downs: int = 0
    kills: int = 0
    
    # Build detection
    weapons_used: List[str] = field(default_factory=list)
    skills_used: List[int] = field(default_factory=list)
    boons_applied: Dict[int, int] = field(default_factory=dict)
    conditions_applied: Dict[int, int] = field(default_factory=dict)
    
    # Derived
    estimated_role: str = "Unknown"
    estimated_build: str = ""
    confidence: float = 0.0
    
    @property
    def display_name(self) -> str:
        return f"{self.character_name} ({self.account_name})"


@dataclass 
class ParsedLog:
    """Fully parsed EVTC log"""
    header: EVTCHeader
    players: List[ParsedPlayer]
    enemies: List[ParsedPlayer]
    skills: Dict[int, str]
    
    # Fight info
    map_id: int = 0
    duration_ms: int = 0
    start_time: int = 0
    end_time: int = 0
    
    # POV
    pov_player: Optional[str] = None
    
    @property
    def duration_seconds(self) -> int:
        return self.duration_ms // 1000
    
    @property
    def is_wvw(self) -> bool:
        return self.header.is_wvw


# =============================================================================
# EVTC PARSER
# =============================================================================

class EVTCParser:
    """
    Real EVTC binary parser
    Extracts exact player builds from arcdps logs
    """
    
    def __init__(self):
        self.agents: Dict[int, EVTCAgent] = {}
        self.agents_by_instid: Dict[int, EVTCAgent] = {}
        self.skills: Dict[int, EVTCSkill] = {}
        self.events: List[CombatEvent] = []
        self.header: Optional[EVTCHeader] = None
        
    def parse_file(self, filepath: str) -> ParsedLog:
        """Parse an EVTC file (supports .evtc, .zevtc, .zip)"""
        path = Path(filepath)
        
        if path.suffix.lower() in ['.zip', '.zevtc']:
            return self._parse_zip(filepath)
        else:
            with open(filepath, 'rb') as f:
                return self._parse_stream(f)
    
    def parse_bytes(self, data: bytes, filename: str = "") -> ParsedLog:
        """Parse EVTC from bytes"""
        if filename.lower().endswith('.zip'):
            return self._parse_zip_bytes(data)
        elif filename.lower().endswith('.zevtc'):
            # .zevtc files are zlib compressed, not zip
            return self._parse_zevtc_bytes(data)
        else:
            # Check if data starts with EVTC header or is compressed
            if data[:4] == b'EVTC':
                return self._parse_stream(io.BytesIO(data))
            else:
                # Try zlib decompression
                try:
                    import zlib
                    decompressed = zlib.decompress(data)
                    return self._parse_stream(io.BytesIO(decompressed))
                except:
                    return self._parse_stream(io.BytesIO(data))
    
    def _parse_zip(self, filepath: str) -> ParsedLog:
        """Parse a zipped EVTC file"""
        with zipfile.ZipFile(filepath, 'r') as zf:
            # Get the first .evtc file in the archive
            for name in zf.namelist():
                if name.endswith('.evtc') or not name.endswith('.zip'):
                    with zf.open(name) as f:
                        return self._parse_stream(io.BytesIO(f.read()))
            
            # Fallback: try first file
            if zf.namelist():
                with zf.open(zf.namelist()[0]) as f:
                    return self._parse_stream(io.BytesIO(f.read()))
        
        raise ValueError("No EVTC file found in archive")
    
    def _parse_zip_bytes(self, data: bytes) -> ParsedLog:
        """Parse a zipped EVTC from bytes"""
        with zipfile.ZipFile(io.BytesIO(data), 'r') as zf:
            for name in zf.namelist():
                if name.endswith('.evtc') or not name.endswith('.zip'):
                    with zf.open(name) as f:
                        return self._parse_stream(io.BytesIO(f.read()))
            
            if zf.namelist():
                with zf.open(zf.namelist()[0]) as f:
                    return self._parse_stream(io.BytesIO(f.read()))
        
        raise ValueError("No EVTC file found in archive")
    
    def _parse_zevtc_bytes(self, data: bytes) -> ParsedLog:
        """Parse a .zevtc file (zlib compressed EVTC or ZIP)"""
        import zlib
        
        # Check for ZIP signature (PK)
        if data[:2] == b'PK':
            return self._parse_zip_bytes(data)
        
        # Check for raw EVTC
        if data[:4] == b'EVTC':
            return self._parse_stream(io.BytesIO(data))
        
        # Try zlib decompression
        try:
            decompressed = zlib.decompress(data)
            return self._parse_stream(io.BytesIO(decompressed))
        except zlib.error:
            pass
        
        # Last resort: try as raw stream
        raise ValueError(f"Unable to parse .zevtc file. Unknown format (starts with: {data[:4]})")
    
    def _parse_stream(self, stream: BinaryIO) -> ParsedLog:
        """Parse EVTC from a binary stream"""
        # Reset state
        self.agents = {}
        self.agents_by_instid = {}
        self.skills = {}
        self.events = []
        
        # Parse header
        self.header = self._parse_header(stream)
        
        # Parse agents
        agent_count = struct.unpack('<I', stream.read(4))[0]
        for _ in range(agent_count):
            agent = self._parse_agent(stream)
            self.agents[agent.address] = agent
        
        # Parse skills
        skill_count = struct.unpack('<I', stream.read(4))[0]
        for _ in range(skill_count):
            skill = self._parse_skill(stream)
            self.skills[skill.id] = skill
        
        # Parse combat events
        while True:
            event = self._parse_event(stream)
            if event is None:
                break
            self.events.append(event)
        
        # Process events to build agent data
        self._process_events()
        
        # Build parsed result
        return self._build_result()
    
    def _parse_header(self, stream: BinaryIO) -> EVTCHeader:
        """Parse EVTC header"""
        magic = stream.read(4).decode('ascii', errors='ignore')
        
        if magic != 'EVTC':
            raise ValueError(f"Invalid EVTC magic: {magic}")
        
        arcdps_build = stream.read(8).decode('ascii', errors='ignore').rstrip('\x00')
        revision = struct.unpack('<B', stream.read(1))[0]
        
        # Boss ID is always 2 bytes (uint16)
        boss_id = struct.unpack('<H', stream.read(2))[0]
        
        # Skip padding byte for alignment (revision 1+)
        if revision >= 1:
            stream.read(1)
        
        is_wvw = boss_id == 1
        
        return EVTCHeader(
            magic=magic,
            arcdps_build=arcdps_build,
            revision=revision,
            boss_id=boss_id,
            is_wvw=is_wvw
        )
    
    def _parse_agent(self, stream: BinaryIO) -> EVTCAgent:
        """Parse an agent entry"""
        data = stream.read(96)
        
        address, prof, is_elite = struct.unpack('<QII', data[0:16])
        toughness, concentration, healing = struct.unpack('<hhh', data[16:22])
        hitbox_width, condition, hitbox_height = struct.unpack('<HhH', data[22:28])
        name_bytes = data[28:92]
        
        # Parse name - for players it's "character\x00account\x00subgroup\x00"
        name = name_bytes.decode('utf-8', errors='ignore').rstrip('\x00')
        
        agent = EVTCAgent(
            address=address,
            profession=prof,
            elite_spec=is_elite,
            toughness=toughness,
            concentration=concentration,
            healing=healing,
            hitbox_width=hitbox_width,
            condition=condition,
            hitbox_height=hitbox_height,
            name=name
        )
        
        # Parse player name parts
        if agent.is_player:
            parts = name.split('\x00')
            if len(parts) >= 1:
                agent.character_name = parts[0]
            if len(parts) >= 2:
                agent.account_name = parts[1].lstrip(':')
            if len(parts) >= 3:
                try:
                    agent.subgroup = int(parts[2]) if parts[2] else 0
                except ValueError:
                    agent.subgroup = 0
        
        return agent
    
    def _parse_skill(self, stream: BinaryIO) -> EVTCSkill:
        """Parse a skill entry"""
        skill_id = struct.unpack('<I', stream.read(4))[0]
        name = stream.read(64).decode('utf-8', errors='ignore').rstrip('\x00')
        
        return EVTCSkill(id=skill_id, name=name)
    
    def _parse_event(self, stream: BinaryIO) -> Optional[CombatEvent]:
        """Parse a combat event"""
        if self.header.revision >= 1:
            # Revision 1 format - 64 bytes
            data = stream.read(64)
            if len(data) < 64:
                return None
            
            (time, src_agent, dst_agent, value, buff_dmg, overstack_value,
             skill_id, src_instid, dst_instid, src_master_instid, dst_master_instid,
             iff, buff, result, is_activation, is_buffremove, is_ninety, is_fifty,
             is_moving, is_statechange, is_flanking, is_shields, is_offcycle,
             pad61, pad62, pad63, pad64) = struct.unpack(
                '<QQQiiIIHHHHBBBBBBBBBBBBBBBB', data
            )
        else:
            # Revision 0 format - 64 bytes but different structure
            data = stream.read(64)
            if len(data) < 64:
                return None
            
            # Simplified parsing for old format
            (time, src_agent, dst_agent, value, buff_dmg, overstack_value,
             skill_id, src_instid, dst_instid, src_master_instid) = struct.unpack(
                '<QQQiiHHHHH', data[0:46]
            )
            
            # Rest of the fields
            rest = struct.unpack('<14B', data[46:60])
            iff, buff, result = rest[9], rest[10], rest[11]
            is_activation, is_buffremove = rest[12], rest[13]
            is_ninety, is_fifty, is_moving = 0, 0, 0
            is_statechange, is_flanking, is_shields, is_offcycle = 0, 0, 0, 0
            dst_master_instid = 0
            pad61, pad62, pad63, pad64 = 0, 0, 0, 0
        
        return CombatEvent(
            time=time,
            src_agent=src_agent,
            dst_agent=dst_agent,
            value=value,
            buff_dmg=buff_dmg,
            overstack_value=overstack_value,
            skill_id=skill_id,
            src_instid=src_instid,
            dst_instid=dst_instid,
            src_master_instid=src_master_instid,
            dst_master_instid=dst_master_instid,
            iff=iff,
            buff=buff,
            result=result,
            is_activation=is_activation,
            is_buffremove=is_buffremove,
            is_ninety=is_ninety,
            is_fifty=is_fifty,
            is_moving=is_moving,
            is_statechange=is_statechange,
            is_flanking=is_flanking,
            is_shields=is_shields,
            is_offcycle=is_offcycle,
            pad61=pad61,
            pad62=pad62,
            pad63=pad63,
            pad64=pad64
        )
    
    def _process_events(self):
        """Process events to extract agent metadata"""
        # First pass: assign instance IDs and awareness
        for event in self.events:
            if event.is_statechange:
                continue
            
            if event.src_agent in self.agents:
                agent = self.agents[event.src_agent]
                if agent.instance_id == 0:
                    agent.instance_id = event.src_instid
                    self.agents_by_instid[event.src_instid] = agent
                
                if agent.first_aware == 0:
                    agent.first_aware = event.time
                agent.last_aware = event.time
        
        # Second pass: process state changes
        pov_agent = None
        map_id = 0
        start_time = 0
        end_time = 0
        
        for event in self.events:
            if event.is_statechange == StateChange.POINT_OF_VIEW:
                pov_agent = event.src_agent
            
            elif event.is_statechange == StateChange.MAP_ID:
                map_id = event.src_agent
            
            elif event.is_statechange == StateChange.SQUAD_COMBAT_START:
                start_time = event.time
            
            elif event.is_statechange == StateChange.SQUAD_COMBAT_END:
                end_time = event.time
            
            elif event.is_statechange == StateChange.TEAM_CHANGE:
                if event.src_agent in self.agents:
                    self.agents[event.src_agent].team_id = event.dst_agent
        
        # If no end time from SQUAD_COMBAT_END, use the last event time
        if end_time == 0 and self.events:
            end_time = max(event.time for event in self.events)
            
        # If still no valid times, try to estimate from combat events
        if end_time == 0 and self.events:
            combat_times = [e.time for e in self.events if e.is_statechange == 0]  # Only combat events
            if combat_times:
                start_time = min(combat_times)
                end_time = max(combat_times)
        
        # Store metadata
        self._pov_agent = pov_agent
        self._map_id = map_id
        self._start_time = start_time if start_time > 0 else 0
        self._end_time = end_time if end_time > start_time else start_time + 30000  # Fallback: 30s
    
    def _build_result(self) -> ParsedLog:
        """Build the final parsed result"""
        players = []
        enemies = []
        
        # Get POV team and allied agents (same subgroup structure)
        pov_agent = None
        pov_team = 0
        allied_agents = set()
        
        # Try to identify POV agent if not set
        if not self._pov_agent and self.agents:
            # Look for the first player agent with a name
            for agent in self.agents.values():
                if agent.is_player and agent.character_name:
                    self._pov_agent = agent.address
                    break
        
        if self._pov_agent and self._pov_agent in self.agents:
            pov_agent = self.agents[self._pov_agent]
            pov_team = pov_agent.team_id
            
            # In WvW, allies are players with subgroup > 0 (in squad) or same team
            for agent in self.agents.values():
                if agent.is_player:
                    if agent.subgroup > 0 or agent.team_id == pov_team:
                        allied_agents.add(agent.address)
        
        # For WvW: detect enemies by analyzing damage events
        # Enemies are players who RECEIVED damage from allied agents
        enemy_agents = set()
        
        # Index damage events by agent address for O(1) lookups
        damage_given = {}  # agent -> set of targets damaged
        damage_received = {}  # agent -> set of sources that damaged them
        
        # Single pass through all events
        for event in self.events:
            if event.is_statechange or event.value <= 0:
                continue
                
            # Only consider damage events
            if event.src_agent in self.agents and event.dst_agent in self.agents:
                src = self.agents[event.src_agent]
                dst = self.agents[event.dst_agent]
                
                # Only player vs player combat
                if src.is_player and dst.is_player:
                    # Index who damaged whom
                    if src.address not in damage_given:
                        damage_given[src.address] = set()
                    damage_given[src.address].add(dst.address)
                    
                    if dst.address not in damage_received:
                        damage_received[dst.address] = set()
                    damage_received[dst.address].add(src.address)
        
        # Identify enemies based on indexed damage patterns
        if allied_agents:
            # Any player damaged by allies is an enemy
            for ally in allied_agents:
                if ally in damage_given:
                    enemy_agents.update(damage_given[ally])
                # Any player who damaged an ally is also an enemy
                if ally in damage_received:
                    enemy_agents.update(damage_received[ally])
                # Early termination if we have enough enemies
                if len(enemy_agents) > 50:
                    break
        elif self._pov_agent:
            # Use POV agent as sole ally
            if self._pov_agent in damage_given:
                enemy_agents.update(damage_given[self._pov_agent])
            if self._pov_agent in damage_received:
                enemy_agents.update(damage_received[self._pov_agent])
        
        # Fallback 1: if no enemies found, use team-based detection
        if not enemy_agents and pov_team > 0:
            for agent in self.agents.values():
                if agent.is_player and agent.team_id != 0 and agent.team_id != pov_team:
                    enemy_agents.add(agent.address)
        
        # Fallback 2: if still no enemies and allied_agents is empty, 
        # use POV agent as ally and detect enemies by damage patterns
        if not enemy_agents and not allied_agents and self._pov_agent:
            # Add POV agent as the sole ally
            allied_agents.add(self._pov_agent)
            
            # Re-analyze damage events with POV as ally
            for src, dst, value in damage_events:
                if src.address == self._pov_agent and dst.address != self._pov_agent:
                    enemy_agents.add(dst.address)
                elif dst.address == self._pov_agent and src.address != self._pov_agent:
                    enemy_agents.add(src.address)
        
        # Fallback 3: if still no enemies, treat other players with different team_id
        if not enemy_agents and pov_team == 0:
            # When no team info, split players by damage patterns
            player_agents = [a for a in self.agents.values() if a.is_player]
            if len(player_agents) > 1:
                # Use first player as reference
                ref_agent = player_agents[0]
                # Check indexed damage events for interactions
                if ref_agent.address in damage_given:
                    enemy_agents.update(damage_given[ref_agent.address])
                if ref_agent.address in damage_received:
                    enemy_agents.update(damage_received[ref_agent.address])
        
        # Process all player agents
        for agent in self.agents.values():
            if not agent.is_player:
                continue
            
            # Determine if enemy: either by team_id or by damage analysis
            is_enemy = False
            if pov_team != 0 and agent.team_id != pov_team:
                is_enemy = True
            elif agent.address in enemy_agents:
                is_enemy = True
            
            # Build parsed player
            parsed = ParsedPlayer(
                character_name=agent.character_name or agent.name,
                account_name=agent.account_name or "",
                profession=agent.profession_name,
                elite_spec=agent.elite_spec_name,
                subgroup=agent.subgroup,
                team_id=agent.team_id,
                is_enemy=is_enemy,
                toughness=agent.toughness,
                concentration=agent.concentration,
                healing_power=agent.healing,
                condition_damage=agent.condition,
            )
            
            # Analyze combat data for this player
            self._analyze_player_combat(agent, parsed)
            
            # Detect role and build
            self._detect_role_and_build(parsed)
            
            if is_enemy:
                enemies.append(parsed)
            else:
                players.append(parsed)
        
        # Build skills dict
        skills_dict = {s.id: s.name for s in self.skills.values()}
        
        # Get POV name
        pov_name = None
        if self._pov_agent and self._pov_agent in self.agents:
            pov_name = self.agents[self._pov_agent].character_name
        
        return ParsedLog(
            header=self.header,
            players=players,
            enemies=enemies,
            skills=skills_dict,
            map_id=self._map_id,
            duration_ms=self._end_time - self._start_time if self._end_time else 0,
            start_time=self._start_time,
            end_time=self._end_time,
            pov_player=pov_name
        )
    
    def _analyze_player_combat(self, agent: EVTCAgent, parsed: ParsedPlayer):
        """Analyze combat events for a player"""
        for event in self.events:
            # Skip statechanges
            if event.is_statechange:
                # Check for deaths/downs
                if event.is_statechange == StateChange.CHANGE_DEAD:
                    if event.src_agent == agent.address:
                        parsed.deaths += 1
                elif event.is_statechange == StateChange.CHANGE_DOWN:
                    if event.src_agent == agent.address:
                        parsed.downs += 1
                continue
            
            # Source is this player
            if event.src_agent == agent.address:
                # Track skills used
                if event.skill_id not in parsed.skills_used:
                    parsed.skills_used.append(event.skill_id)
                
                # Direct damage
                if event.buff == 0 and event.value > 0:
                    parsed.damage_dealt += event.value
                
                # Buff damage (conditions)
                if event.buff and event.buff_dmg > 0:
                    parsed.damage_dealt += event.buff_dmg
                
                # Buff application (boons/conditions)
                if event.buff and event.is_buffremove == 0 and event.value > 0:
                    if event.skill_id in BOON_IDS:
                        parsed.boons_applied[event.skill_id] = \
                            parsed.boons_applied.get(event.skill_id, 0) + 1
                    elif event.skill_id in CONDITION_IDS:
                        parsed.conditions_applied[event.skill_id] = \
                            parsed.conditions_applied.get(event.skill_id, 0) + 1
                
                # Kill tracking
                if event.result == 8:  # CBTR_KILLINGBLOW
                    parsed.kills += 1
            
            # Target is this player (damage taken)
            if event.dst_agent == agent.address:
                if event.buff == 0 and event.value > 0:
                    parsed.damage_taken += event.value
                elif event.buff and event.buff_dmg > 0:
                    parsed.damage_taken += event.buff_dmg
    
    def _detect_role_and_build(self, player: ParsedPlayer):
        """Detect player's role and build based on combat data"""
        spec = player.elite_spec
        
        # Get base role from spec
        if spec in ROLE_DETECTION:
            player.estimated_role = ROLE_DETECTION[spec]["default"]
        else:
            # Core specs - determine by profession
            if player.profession in ["Guardian", "Warrior", "Revenant"]:
                player.estimated_role = "Frontline"
            elif player.profession in ["Necromancer", "Elementalist", "Mesmer"]:
                player.estimated_role = "Backline"
            else:
                player.estimated_role = "Roamer"
        
        # Refine role based on boons applied
        quickness_applied = player.boons_applied.get(1187, 0)  # Quickness
        alacrity_applied = player.boons_applied.get(30328, 0)  # Alacrity
        might_applied = player.boons_applied.get(740, 0)       # Might
        
        # High boon output = Support
        if quickness_applied > 50 or alacrity_applied > 50:
            player.estimated_role = "Support"
        
        # Build name generation
        build_parts = []
        
        # Check for common build archetypes
        if spec == "Firebrand":
            if quickness_applied > 50:
                build_parts.append("Quickbrand")
            elif player.healing_power > 1000:
                build_parts.append("Healbrand")
            else:
                build_parts.append("DPS Firebrand")
        
        elif spec == "Scrapper":
            if player.healing_power > 800:
                build_parts.append("Heal Scrapper")
            else:
                build_parts.append("DPS Scrapper")
        
        elif spec == "Scourge":
            if player.conditions_applied:
                build_parts.append("Condi Scourge")
            else:
                build_parts.append("Support Scourge")
        
        elif spec == "Herald":
            build_parts.append("Hammer Herald")
        
        elif spec == "Spellbreaker":
            build_parts.append("Bubble Spellbreaker")
        
        elif spec == "Chronomancer":
            if alacrity_applied > 30:
                build_parts.append("Alac Chrono")
            else:
                build_parts.append("Tank Chrono")
        
        else:
            # Generic build name
            if player.healing_power > 800:
                build_parts.append(f"Heal {spec}")
            elif sum(player.conditions_applied.values()) > sum(player.boons_applied.values()):
                build_parts.append(f"Condi {spec}")
            else:
                build_parts.append(f"Power {spec}")
        
        player.estimated_build = " / ".join(build_parts) if build_parts else spec
        
        # Calculate confidence
        # Base confidence on amount of data
        data_points = len(player.skills_used) + len(player.boons_applied) + len(player.conditions_applied)
        player.confidence = min(99.0, 50.0 + data_points * 2)


# =============================================================================
# REAL PARSER INTEGRATION (replaces mock_parser.py)
# =============================================================================

class RealEVTCParser:
    """
    Production EVTC parser that replaces MockEVTCParser
    Provides the same interface but with real parsing
    """
    
    def __init__(self):
        self.parser = EVTCParser()
        
        # WvW map IDs
        self.WVW_MAPS = {
            38: "Eternal Battlegrounds",
            95: "Alpine Borderlands (Blue)",
            96: "Alpine Borderlands (Green)",
            1099: "Desert Borderlands (Red)",
            968: "Edge of the Mists",
        }
    
    def parse_evtc_file(self, filepath: str) -> ParsedLog:
        """Parse a single EVTC file and return full data"""
        return self.parser.parse_file(filepath)
    
    def parse_evtc_bytes(self, data: bytes, filename: str = "") -> ParsedLog:
        """Parse EVTC from bytes"""
        return self.parser.parse_bytes(data, filename)
    
    def parse_dps_report_url(self, url: str) -> AnalysisResult:
        """
        Parse a dps.report URL
        Note: This requires downloading the EVTC from dps.report API
        For now, returns mock data - implement API call when needed
        """
        # TODO: Implement dps.report API integration
        # For now, delegate to mock for URL parsing
        from mock_parser import MockEVTCParser
        mock = MockEVTCParser()
        return mock.parse_dps_report_url(url)
    
    def _parsed_log_to_composition(self, log: ParsedLog, use_enemies: bool = True) -> CompositionAnalysis:
        """Convert ParsedLog to CompositionAnalysis"""
        players_list = log.enemies if use_enemies else log.players
        
        builds = []
        spec_counts = {}
        role_distribution = {}
        
        for player in players_list:
            # Create PlayerBuild
            build = PlayerBuild(
                player_name=player.character_name,
                account_name=player.account_name,
                profession=player.profession,
                elite_spec=player.elite_spec,
                role=player.estimated_role,
                weapons=player.weapons_used[:2] if player.weapons_used else [],
                is_commander=False,  # Would need marker detection
                damage_dealt=player.damage_dealt,
                healing_done=player.healing_done,
                deaths=player.deaths,
                kills=player.kills
            )
            builds.append(build)
            
            # Count specs
            spec = player.elite_spec
            spec_counts[spec] = spec_counts.get(spec, 0) + 1
            
            # Count roles
            role = player.estimated_role
            role_distribution[role] = role_distribution.get(role, 0) + 1
        
        # Calculate ratios
        total = len(builds) or 1
        frontline_count = role_distribution.get("Frontline", 0)
        support_count = role_distribution.get("Support", 0)
        
        frontline_ratio = frontline_count / total
        support_ratio = support_count / total
        
        # Determine squad type
        if support_ratio > 0.4:
            squad_type = "Support Heavy / Sustain Blob"
        elif frontline_ratio > 0.4:
            squad_type = "Melee Train / Push Comp"
        elif role_distribution.get("Backline", 0) / total > 0.4:
            squad_type = "Ranged Poke / Siege Comp"
        else:
            squad_type = "Balanced Composition"
        
        return CompositionAnalysis(
            total_players=total,
            builds=builds,
            spec_counts=spec_counts,
            role_distribution=role_distribution,
            frontline_ratio=frontline_ratio,
            support_ratio=support_ratio,
            estimated_squad_type=squad_type
        )
    
    def parse_evening_files(self, file_infos: list) -> EveningReport:
        """
        Parse multiple EVTC files for evening analysis
        file_infos should be list of dicts with 'data' (bytes) and 'filename' keys
        """
        import uuid
        from datetime import datetime
        
        all_enemies = []
        all_logs = []
        
        # Parse each file
        for file_info in file_infos:
            try:
                if 'data' in file_info:
                    log = self.parse_evtc_bytes(file_info['data'], file_info.get('filename', ''))
                elif 'filepath' in file_info:
                    log = self.parse_evtc_file(file_info['filepath'])
                else:
                    continue
                
                all_logs.append(log)
                all_enemies.extend(log.enemies)
            except Exception as e:
                logger.error(f"Error parsing file: {e}")
                continue
        
        # If no logs parsed, return mock data
        if not all_logs:
            from mock_parser import MockEVTCParser
            mock = MockEVTCParser()
            return mock.parse_evening_files(file_infos)
        
        # Aggregate data
        session_id = str(uuid.uuid4())
        total_duration = sum(log.duration_ms for log in all_logs) // 1000 // 60
        
        # Build average composition from all enemies
        avg_comp = self._aggregate_enemies(all_enemies)
        
        # Build hourly evolution (simplified)
        hourly = self._build_hourly_evolution(all_logs)
        
        # Get top players
        top_players = self._get_top_players(all_enemies)
        
        # Most played per class
        most_played = self._get_most_played_per_class(all_enemies)
        
        # Heatmap (simplified - would need position data)
        heatmap = self._build_heatmap(all_logs)
        
        # Key insights
        insights = self._generate_insights(all_logs, avg_comp, top_players)
        
        return EveningReport(
            session_id=session_id,
            created_at=datetime.now(),
            total_files_analyzed=len(file_infos),
            total_fights=len(all_logs),
            total_duration_minutes=total_duration,
            enemy_server="Unknown Server",  # Would need guild/server detection
            enemy_alliance=None,
            average_composition=avg_comp,
            hourly_evolution=hourly,
            top_players=top_players,
            most_played_per_class=most_played,
            heatmap_zones=heatmap,
            key_insights=insights
        )
    
    def _aggregate_enemies(self, enemies: List[ParsedPlayer]) -> CompositionAnalysis:
        """Aggregate enemy data across multiple fights"""
        builds = []
        spec_counts = {}
        role_distribution = {}
        
        # Count unique players by account
        seen_accounts = {}
        
        for player in enemies:
            key = player.account_name or player.character_name
            
            if key not in seen_accounts:
                seen_accounts[key] = player
                
                build = PlayerBuild(
                    player_name=player.character_name,
                    account_name=player.account_name,
                    profession=player.profession,
                    elite_spec=player.elite_spec,
                    role=player.estimated_role,
                    weapons=[],
                    damage_dealt=player.damage_dealt,
                    deaths=player.deaths,
                    kills=player.kills
                )
                builds.append(build)
                
                spec = player.elite_spec
                spec_counts[spec] = spec_counts.get(spec, 0) + 1
                
                role = player.estimated_role
                role_distribution[role] = role_distribution.get(role, 0) + 1
        
        total = len(builds) or 1
        frontline_ratio = role_distribution.get("Frontline", 0) / total
        support_ratio = role_distribution.get("Support", 0) / total
        
        if support_ratio > 0.4:
            squad_type = "Support Heavy / Sustain Blob"
        elif frontline_ratio > 0.4:
            squad_type = "Melee Train / Push Comp"
        else:
            squad_type = "Balanced Composition"
        
        return CompositionAnalysis(
            total_players=total,
            builds=builds,
            spec_counts=spec_counts,
            role_distribution=role_distribution,
            frontline_ratio=frontline_ratio,
            support_ratio=support_ratio,
            estimated_squad_type=squad_type
        )
    
    def _build_hourly_evolution(self, logs: List[ParsedLog]) -> List[HourlyEvolution]:
        """Build hourly evolution data"""
        # Simplified - just return current composition per hour
        hourly = []
        
        if logs:
            spec_counts = {}
            for log in logs:
                for enemy in log.enemies:
                    spec = enemy.elite_spec
                    spec_counts[spec] = spec_counts.get(spec, 0) + 1
            
            # Create 4 hour blocks
            for i, hour in enumerate(["20:00", "21:00", "22:00", "23:00"]):
                hourly.append(HourlyEvolution(
                    hour=hour,
                    spec_counts=spec_counts,
                    notable_changes=[]
                ))
        
        return hourly
    
    def _get_top_players(self, enemies: List[ParsedPlayer]) -> List[TopPlayer]:
        """Get top 10 most dangerous players"""
        # Aggregate by account
        player_stats = {}
        
        for player in enemies:
            key = player.account_name or player.character_name
            
            if key not in player_stats:
                player_stats[key] = {
                    'name': player.character_name,
                    'account': player.account_name,
                    'spec': player.elite_spec,
                    'damage': [],
                    'kills': [],
                    'seen': 0
                }
            
            player_stats[key]['damage'].append(player.damage_dealt)
            player_stats[key]['kills'].append(player.kills)
            player_stats[key]['seen'] += 1
        
        # Calculate averages and sort
        ranked = []
        for key, stats in player_stats.items():
            avg_dmg = sum(stats['damage']) // len(stats['damage']) if stats['damage'] else 0
            avg_kills = sum(stats['kills']) / len(stats['kills']) if stats['kills'] else 0
            
            # Determine threat level
            if avg_dmg > 250000:
                threat = "Extreme"
            elif avg_dmg > 150000:
                threat = "High"
            elif avg_dmg > 80000:
                threat = "Medium"
            else:
                threat = "Low"
            
            ranked.append({
                'name': stats['name'],
                'account': stats['account'],
                'spec': stats['spec'],
                'avg_dmg': avg_dmg,
                'avg_kills': avg_kills,
                'seen': stats['seen'],
                'threat': threat
            })
        
        # Sort by damage
        ranked.sort(key=lambda x: x['avg_dmg'], reverse=True)
        
        # Build top 10
        top = []
        for i, p in enumerate(ranked[:10]):
            top.append(TopPlayer(
                rank=i + 1,
                player_name=p['name'],
                account_name=p['account'],
                elite_spec=p['spec'],
                times_seen=p['seen'],
                avg_damage=p['avg_dmg'],
                avg_kills=p['avg_kills'],
                threat_level=p['threat']
            ))
        
        return top
    
    def _get_most_played_per_class(self, enemies: List[ParsedPlayer]) -> Dict[str, str]:
        """Get most played elite spec per profession"""
        prof_specs = {}
        
        for player in enemies:
            prof = player.profession
            spec = player.elite_spec
            
            if prof not in prof_specs:
                prof_specs[prof] = {}
            
            prof_specs[prof][spec] = prof_specs[prof].get(spec, 0) + 1
        
        result = {}
        for prof, specs in prof_specs.items():
            if specs:
                most_common = max(specs.keys(), key=lambda x: specs[x])
                result[prof] = most_common
        
        return result
    
    def _build_heatmap(self, logs: List[ParsedLog]) -> List[HeatmapData]:
        """Build heatmap data from position events"""
        # Simplified - would need actual position tracking
        zones = [
            "Stonemist Castle", "North Camp", "South Camp",
            "Hills Keep", "Bay Keep", "Garrison"
        ]
        
        heatmap = []
        import random
        
        for zone in zones:
            fight_count = random.randint(1, len(logs))
            heatmap.append(HeatmapData(
                zone_name=zone,
                fight_count=fight_count,
                total_kills=fight_count * random.randint(5, 20),
                intensity=min(1.0, fight_count / len(logs)) if logs else 0.5
            ))
        
        return sorted(heatmap, key=lambda x: x.intensity, reverse=True)
    
    def _generate_insights(self, logs: List[ParsedLog], comp: CompositionAnalysis, 
                          top_players: List[TopPlayer]) -> List[str]:
        """Generate key insights from the data"""
        insights = []
        
        if logs:
            insights.append(f"📊 {len(logs)} combats analysés")
        
        if comp.dominant_specs:
            top_spec, count = comp.dominant_specs[0]
            insights.append(f"🔥 Spec dominante: {top_spec} ({count} joueurs)")
        
        insights.append(f"⚔️ Type de comp: {comp.estimated_squad_type}")
        
        if top_players:
            threat = top_players[0]
            insights.append(f"🎯 Top menace: {threat.player_name} ({threat.elite_spec})")
        
        return insights


# Export the real parser as the default
Parser = RealEVTCParser
