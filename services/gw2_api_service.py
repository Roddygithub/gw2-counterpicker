"""
GW2 API Integration Service
Handles all interactions with the Guild Wars 2 official API
"""

import httpx
import hashlib
import os
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from cryptography.fernet import Fernet
from tinydb import TinyDB, Query
from pathlib import Path
from logger import get_logger

logger = get_logger('gw2_api')

# GW2 API Base URL
GW2_API_BASE = "https://api.guildwars2.com/v2"

# Required scopes for our features
REQUIRED_SCOPES = ["account", "characters", "builds", "progression"]

# Encryption key - in production, use environment variable
ENCRYPTION_KEY = os.environ.get('GW2_API_ENCRYPTION_KEY', Fernet.generate_key())
cipher = Fernet(ENCRYPTION_KEY if isinstance(ENCRYPTION_KEY, bytes) else ENCRYPTION_KEY.encode())

# Database for storing API keys
db_path = Path(__file__).parent.parent / "data" / "api_keys.json"
db_path.parent.mkdir(parents=True, exist_ok=True)
api_keys_db = TinyDB(str(db_path))


@dataclass
class GW2Account:
    """GW2 Account information"""
    account_id: str
    account_name: str
    world: int
    world_name: str = ""
    guilds: List[str] = None
    access: List[str] = None  # ["GuildWars2", "HeartOfThorns", "PathOfFire", "EndOfDragons", "SecretsOfTheObscure"]
    commander: bool = False
    fractal_level: int = 0
    wvw_rank: int = 0
    created: str = ""
    
    def __post_init__(self):
        if self.guilds is None:
            self.guilds = []
        if self.access is None:
            self.access = []
    
    def has_expansion(self, expansion: str) -> bool:
        """Check if account has a specific expansion"""
        expansion_map = {
            "hot": "HeartOfThorns",
            "pof": "PathOfFire", 
            "eod": "EndOfDragons",
            "soto": "SecretsOfTheObscure"
        }
        exp_name = expansion_map.get(expansion.lower(), expansion)
        return exp_name in self.access
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class GW2Character:
    """GW2 Character information"""
    name: str
    profession: str
    race: str
    level: int
    age: int  # seconds played
    created: str
    specializations: Dict[str, List[Dict]] = None  # {"pve": [...], "pvp": [...], "wvw": [...]}
    equipment: List[Dict] = None
    
    def __post_init__(self):
        if self.specializations is None:
            self.specializations = {}
        if self.equipment is None:
            self.equipment = []
    
    def get_wvw_elite_spec(self) -> Optional[str]:
        """Get the elite specialization used in WvW"""
        wvw_specs = self.specializations.get("wvw", [])
        for spec in wvw_specs:
            if spec and spec.get("id"):
                # Elite specs have higher IDs
                return spec.get("name", "")
        return None
    
    def to_dict(self) -> Dict:
        return asdict(self)


# Elite specialization requirements by expansion
ELITE_SPEC_EXPANSIONS = {
    # Heart of Thorns
    "Dragonhunter": "hot", "Firebrand": "pof", "Willbender": "eod",
    "Berserker": "hot", "Spellbreaker": "pof", "Bladesworn": "eod",
    "Herald": "hot", "Renegade": "pof", "Vindicator": "eod",
    "Scrapper": "hot", "Holosmith": "pof", "Mechanist": "eod",
    "Druid": "hot", "Soulbeast": "pof", "Untamed": "eod",
    "Daredevil": "hot", "Deadeye": "pof", "Specter": "eod",
    "Tempest": "hot", "Weaver": "pof", "Catalyst": "eod",
    "Chronomancer": "hot", "Mirage": "pof", "Virtuoso": "eod",
    "Reaper": "hot", "Scourge": "pof", "Harbinger": "eod",
}


class GW2APIService:
    """Service for interacting with GW2 API"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def validate_api_key(self, api_key: str) -> Dict[str, Any]:
        """Validate an API key and return token info"""
        try:
            response = await self.client.get(
                f"{GW2_API_BASE}/tokeninfo",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            
            if response.status_code == 200:
                token_info = response.json()
                permissions = token_info.get("permissions", [])
                
                # Check required scopes
                missing_scopes = [s for s in REQUIRED_SCOPES if s not in permissions]
                
                return {
                    "valid": True,
                    "id": token_info.get("id"),
                    "name": token_info.get("name"),
                    "permissions": permissions,
                    "missing_scopes": missing_scopes,
                    "has_all_scopes": len(missing_scopes) == 0
                }
            elif response.status_code == 401:
                return {"valid": False, "error": "Clé API invalide"}
            else:
                return {"valid": False, "error": f"Erreur API: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"API key validation error: {e}")
            return {"valid": False, "error": str(e)}
    
    async def get_account(self, api_key: str) -> Optional[GW2Account]:
        """Get account information"""
        try:
            response = await self.client.get(
                f"{GW2_API_BASE}/account",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Get world name
                world_name = await self._get_world_name(data.get("world", 0))
                
                return GW2Account(
                    account_id=data.get("id", ""),
                    account_name=data.get("name", ""),
                    world=data.get("world", 0),
                    world_name=world_name,
                    guilds=data.get("guilds", []),
                    access=data.get("access", []),
                    commander=data.get("commander", False),
                    fractal_level=data.get("fractal_level", 0),
                    wvw_rank=data.get("wvw_rank", 0),
                    created=data.get("created", "")
                )
            return None
            
        except Exception as e:
            logger.error(f"Get account error: {e}")
            return None
    
    async def get_characters(self, api_key: str) -> List[GW2Character]:
        """Get all characters with their builds"""
        try:
            # Get character names
            response = await self.client.get(
                f"{GW2_API_BASE}/characters",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            
            if response.status_code != 200:
                return []
            
            char_names = response.json()
            characters = []
            
            # Get details for each character
            for name in char_names:
                char_data = await self._get_character_details(api_key, name)
                if char_data:
                    characters.append(char_data)
            
            return characters
            
        except Exception as e:
            logger.error(f"Get characters error: {e}")
            return []
    
    async def _get_character_details(self, api_key: str, name: str) -> Optional[GW2Character]:
        """Get detailed character info including builds"""
        try:
            response = await self.client.get(
                f"{GW2_API_BASE}/characters/{name}",
                headers={"Authorization": f"Bearer {api_key}"},
                params={"v": "2021-07-15T13:00:00.000Z"}  # Schema version for builds
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract specializations for each game mode
                specs = {}
                if "specializations" in data:
                    specs = data["specializations"]
                
                return GW2Character(
                    name=data.get("name", ""),
                    profession=data.get("profession", ""),
                    race=data.get("race", ""),
                    level=data.get("level", 0),
                    age=data.get("age", 0),
                    created=data.get("created", ""),
                    specializations=specs,
                    equipment=data.get("equipment", [])
                )
            return None
            
        except Exception as e:
            logger.error(f"Get character details error for {name}: {e}")
            return None
    
    async def _get_world_name(self, world_id: int) -> str:
        """Get world name from ID"""
        try:
            response = await self.client.get(
                f"{GW2_API_BASE}/worlds/{world_id}"
            )
            if response.status_code == 200:
                return response.json().get("name", "")
            return ""
        except:
            return ""
    
    async def get_guild_info(self, guild_id: str, api_key: str = None) -> Optional[Dict]:
        """Get guild information"""
        try:
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            
            response = await self.client.get(
                f"{GW2_API_BASE}/guild/{guild_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            return None
            
        except Exception as e:
            logger.error(f"Get guild info error: {e}")
            return None
    
    def get_available_elite_specs(self, account: GW2Account) -> List[str]:
        """Get list of elite specs available based on account expansions"""
        available = []
        for spec, expansion in ELITE_SPEC_EXPANSIONS.items():
            if account.has_expansion(expansion):
                available.append(spec)
        return available
    
    def can_play_spec(self, account: GW2Account, spec_name: str) -> bool:
        """Check if account can play a specific elite spec"""
        expansion = ELITE_SPEC_EXPANSIONS.get(spec_name)
        if not expansion:
            return True  # Core specs are always available
        return account.has_expansion(expansion)


# API Key storage functions
def encrypt_api_key(api_key: str) -> str:
    """Encrypt an API key for storage"""
    return cipher.encrypt(api_key.encode()).decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt a stored API key"""
    return cipher.decrypt(encrypted_key.encode()).decode()


def hash_api_key(api_key: str) -> str:
    """Create a hash of the API key for identification"""
    return hashlib.sha256(api_key.encode()).hexdigest()[:16]


def store_api_key(account_id: str, account_name: str, api_key: str, session_id: str) -> bool:
    """Store an encrypted API key"""
    try:
        ApiKey = Query()
        encrypted = encrypt_api_key(api_key)
        key_hash = hash_api_key(api_key)
        
        # Check if already exists
        existing = api_keys_db.search(ApiKey.account_id == account_id)
        
        data = {
            "account_id": account_id,
            "account_name": account_name,
            "encrypted_key": encrypted,
            "key_hash": key_hash,
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "last_used": datetime.now().isoformat()
        }
        
        if existing:
            api_keys_db.update(data, ApiKey.account_id == account_id)
        else:
            api_keys_db.insert(data)
        
        logger.info(f"API key stored for account: {account_name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to store API key: {e}")
        return False


def get_api_key_by_session(session_id: str) -> Optional[str]:
    """Retrieve API key for a session"""
    try:
        ApiKey = Query()
        result = api_keys_db.search(ApiKey.session_id == session_id)
        
        if result:
            # Update last used
            api_keys_db.update(
                {"last_used": datetime.now().isoformat()},
                ApiKey.session_id == session_id
            )
            return decrypt_api_key(result[0]["encrypted_key"])
        return None
        
    except Exception as e:
        logger.error(f"Failed to retrieve API key: {e}")
        return None


def get_account_by_session(session_id: str) -> Optional[Dict]:
    """Get stored account info for a session"""
    try:
        ApiKey = Query()
        result = api_keys_db.search(ApiKey.session_id == session_id)
        
        if result:
            return {
                "account_id": result[0]["account_id"],
                "account_name": result[0]["account_name"],
                "created_at": result[0]["created_at"],
                "last_used": result[0]["last_used"]
            }
        return None
        
    except Exception as e:
        logger.error(f"Failed to get account info: {e}")
        return None


def delete_api_key(session_id: str) -> bool:
    """Delete API key for a session"""
    try:
        ApiKey = Query()
        api_keys_db.remove(ApiKey.session_id == session_id)
        logger.info(f"API key deleted for session: {session_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to delete API key: {e}")
        return False


# Singleton instance
gw2_api = GW2APIService()
