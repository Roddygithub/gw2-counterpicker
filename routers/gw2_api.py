"""
GW2 API Integration Routes
Handles API key management and account features
"""

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from pathlib import Path

from services.gw2_api_service import (
    gw2_api, GW2Account, GW2Character,
    store_api_key, get_api_key_by_session, get_account_by_session,
    delete_api_key, REQUIRED_SCOPES, ELITE_SPEC_EXPANSIONS
)
from services.player_stats_service import (
    get_player_fights, get_player_career_stats, get_player_spec_stats,
    get_guild_stats, record_player_fight
)
from logger import get_logger

logger = get_logger('gw2_api_routes')

router = APIRouter(prefix="/api/gw2", tags=["GW2 API"])

# Templates
templates_path = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_path))


@router.post("/connect")
async def connect_api_key(
    request: Request,
    api_key: str = Form(...)
):
    """Connect a GW2 API key to the session"""
    try:
        # Get or create session ID
        session_id = request.cookies.get("session_id")
        if not session_id:
            import uuid
            session_id = str(uuid.uuid4())
        
        # Validate the API key
        validation = await gw2_api.validate_api_key(api_key)
        
        if not validation["valid"]:
            return JSONResponse({
                "success": False,
                "error": validation.get("error", "Clé API invalide")
            }, status_code=400)
        
        if not validation["has_all_scopes"]:
            missing = validation["missing_scopes"]
            return JSONResponse({
                "success": False,
                "error": f"Scopes manquants: {', '.join(missing)}",
                "missing_scopes": missing,
                "required_scopes": REQUIRED_SCOPES
            }, status_code=400)
        
        # Get account info
        account = await gw2_api.get_account(api_key)
        if not account:
            return JSONResponse({
                "success": False,
                "error": "Impossible de récupérer les informations du compte"
            }, status_code=400)
        
        # Store the API key
        stored = store_api_key(
            account_id=account.account_id,
            account_name=account.account_name,
            api_key=api_key,
            session_id=session_id
        )
        
        if not stored:
            return JSONResponse({
                "success": False,
                "error": "Erreur lors de l'enregistrement de la clé"
            }, status_code=500)
        
        # Get available elite specs
        available_specs = gw2_api.get_available_elite_specs(account)
        
        response = JSONResponse({
            "success": True,
            "account": {
                "name": account.account_name,
                "world": account.world_name,
                "wvw_rank": account.wvw_rank,
                "commander": account.commander,
                "access": account.access,
                "available_elite_specs": available_specs
            },
            "message": f"Connecté en tant que {account.account_name}"
        })
        
        # Set session cookie if new
        response.set_cookie(
            key="session_id",
            value=session_id,
            max_age=60*60*24*30,  # 30 days
            httponly=True,
            samesite="lax"
        )
        
        logger.info(f"API key connected for account: {account.account_name}")
        return response
        
    except Exception as e:
        logger.error(f"Connect API key error: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@router.get("/account")
async def get_account_info(request: Request):
    """Get current connected account info"""
    try:
        session_id = request.cookies.get("session_id")
        if not session_id:
            return JSONResponse({
                "connected": False,
                "message": "Aucune session active"
            })
        
        api_key = get_api_key_by_session(session_id)
        if not api_key:
            return JSONResponse({
                "connected": False,
                "message": "Aucune clé API enregistrée"
            })
        
        # Get fresh account data
        account = await gw2_api.get_account(api_key)
        if not account:
            return JSONResponse({
                "connected": False,
                "error": "Clé API invalide ou expirée"
            })
        
        available_specs = gw2_api.get_available_elite_specs(account)
        
        return JSONResponse({
            "connected": True,
            "account": {
                "id": account.account_id,
                "name": account.account_name,
                "world": account.world_name,
                "wvw_rank": account.wvw_rank,
                "commander": account.commander,
                "access": account.access,
                "guilds": account.guilds,
                "available_elite_specs": available_specs
            }
        })
        
    except Exception as e:
        logger.error(f"Get account info error: {e}")
        return JSONResponse({
            "connected": False,
            "error": str(e)
        }, status_code=500)


@router.get("/characters")
async def get_characters(request: Request):
    """Get all characters for connected account"""
    try:
        session_id = request.cookies.get("session_id")
        if not session_id:
            return JSONResponse({
                "success": False,
                "error": "Non connecté"
            }, status_code=401)
        
        api_key = get_api_key_by_session(session_id)
        if not api_key:
            return JSONResponse({
                "success": False,
                "error": "Clé API non trouvée"
            }, status_code=401)
        
        characters = await gw2_api.get_characters(api_key)
        
        # Convert to dict and add useful info
        chars_data = []
        for char in characters:
            char_dict = char.to_dict()
            char_dict["hours_played"] = round(char.age / 3600, 1)
            char_dict["wvw_elite_spec"] = char.get_wvw_elite_spec()
            chars_data.append(char_dict)
        
        # Sort by level and playtime
        chars_data.sort(key=lambda x: (-x["level"], -x["age"]))
        
        return JSONResponse({
            "success": True,
            "characters": chars_data,
            "total": len(chars_data)
        })
        
    except Exception as e:
        logger.error(f"Get characters error: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@router.post("/disconnect")
async def disconnect_api_key(request: Request):
    """Disconnect and delete stored API key"""
    try:
        session_id = request.cookies.get("session_id")
        if not session_id:
            return JSONResponse({
                "success": False,
                "error": "Aucune session active"
            })
        
        deleted = delete_api_key(session_id)
        
        response = JSONResponse({
            "success": True,
            "message": "Clé API supprimée avec succès"
        })
        
        # Clear the session cookie
        response.delete_cookie("session_id")
        
        return response
        
    except Exception as e:
        logger.error(f"Disconnect error: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@router.get("/recommendations")
async def get_personalized_recommendations(
    request: Request,
    enemy_comp: str = ""
):
    """Get AI recommendations filtered by account capabilities"""
    try:
        session_id = request.cookies.get("session_id")
        
        # Base recommendations (would come from counter_ai normally)
        base_recommendations = [
            {"spec": "Spellbreaker", "role": "strip", "count": 2},
            {"spec": "Harbinger", "role": "dps", "count": 2},
            {"spec": "Firebrand", "role": "support", "count": 2},
            {"spec": "Scrapper", "role": "support", "count": 1},
            {"spec": "Virtuoso", "role": "dps", "count": 2},
        ]
        
        if not session_id:
            # Return generic recommendations
            return JSONResponse({
                "personalized": False,
                "recommendations": base_recommendations,
                "message": "Connectez votre clé API pour des recommandations personnalisées"
            })
        
        api_key = get_api_key_by_session(session_id)
        if not api_key:
            return JSONResponse({
                "personalized": False,
                "recommendations": base_recommendations
            })
        
        # Get account and characters
        account = await gw2_api.get_account(api_key)
        characters = await gw2_api.get_characters(api_key)
        
        if not account:
            return JSONResponse({
                "personalized": False,
                "recommendations": base_recommendations
            })
        
        # Get player's available specs
        available_specs = gw2_api.get_available_elite_specs(account)
        
        # Get specs the player actually has characters for
        player_professions = set()
        player_specs = set()
        for char in characters:
            if char.level >= 80:
                player_professions.add(char.profession)
                wvw_spec = char.get_wvw_elite_spec()
                if wvw_spec:
                    player_specs.add(wvw_spec)
        
        # Filter and adapt recommendations
        personalized_recs = []
        alternatives = []
        
        for rec in base_recommendations:
            spec = rec["spec"]
            
            # Check if player can play this spec
            if spec in available_specs:
                # Check if they have a character for it
                has_char = any(
                    ELITE_SPEC_EXPANSIONS.get(spec, "") == "" or 
                    char.profession.lower() in spec.lower()
                    for char in characters if char.level >= 80
                )
                
                rec_copy = rec.copy()
                rec_copy["available"] = True
                rec_copy["has_character"] = spec in player_specs
                
                if spec in player_specs:
                    rec_copy["priority"] = "high"
                    rec_copy["note"] = "Tu joues déjà cette spé !"
                else:
                    rec_copy["priority"] = "medium"
                    rec_copy["note"] = "Tu as l'extension nécessaire"
                
                personalized_recs.append(rec_copy)
            else:
                # Suggest alternative
                rec_copy = rec.copy()
                rec_copy["available"] = False
                rec_copy["priority"] = "low"
                rec_copy["note"] = f"Nécessite une extension que tu n'as pas"
                alternatives.append(rec_copy)
        
        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        personalized_recs.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 3))
        
        return JSONResponse({
            "personalized": True,
            "account_name": account.account_name,
            "recommendations": personalized_recs,
            "alternatives": alternatives,
            "player_specs": list(player_specs),
            "available_specs": available_specs
        })
        
    except Exception as e:
        logger.error(f"Get recommendations error: {e}")
        return JSONResponse({
            "personalized": False,
            "error": str(e)
        }, status_code=500)


# Page routes
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Personal dashboard page"""
    session_id = request.cookies.get("session_id")
    connected = False
    account_info = None
    
    if session_id:
        api_key = get_api_key_by_session(session_id)
        if api_key:
            account = await gw2_api.get_account(api_key)
            if account:
                connected = True
                account_info = account.to_dict()
                account_info["available_elite_specs"] = gw2_api.get_available_elite_specs(account)
    
    lang = request.cookies.get("lang", "fr")
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "connected": connected,
            "account": account_info,
            "lang": lang,
            "required_scopes": REQUIRED_SCOPES
        }
    )


# ==================== PLAYER STATS ENDPOINTS ====================

@router.get("/stats")
async def get_my_stats(request: Request):
    """Get career stats for connected account"""
    try:
        session_id = request.cookies.get("session_id")
        if not session_id:
            return JSONResponse({
                "success": False,
                "error": "Non connecté"
            }, status_code=401)
        
        account_info = get_account_by_session(session_id)
        if not account_info:
            return JSONResponse({
                "success": False,
                "error": "Compte non trouvé"
            }, status_code=401)
        
        career_stats = get_player_career_stats(account_info["account_id"])
        
        if not career_stats:
            return JSONResponse({
                "success": True,
                "has_data": False,
                "message": "Aucun combat enregistré. Analysez des logs pour commencer à tracker vos stats !"
            })
        
        return JSONResponse({
            "success": True,
            "has_data": True,
            "stats": career_stats.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Get stats error: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@router.get("/stats/specs")
async def get_my_spec_stats(request: Request):
    """Get stats per specialization for connected account"""
    try:
        session_id = request.cookies.get("session_id")
        if not session_id:
            return JSONResponse({"success": False, "error": "Non connecté"}, status_code=401)
        
        account_info = get_account_by_session(session_id)
        if not account_info:
            return JSONResponse({"success": False, "error": "Compte non trouvé"}, status_code=401)
        
        spec_stats = get_player_spec_stats(account_info["account_id"])
        
        return JSONResponse({
            "success": True,
            "specs": spec_stats
        })
        
    except Exception as e:
        logger.error(f"Get spec stats error: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.get("/fights")
async def get_my_fights(request: Request, limit: int = 50):
    """Get recent fights for connected account"""
    try:
        session_id = request.cookies.get("session_id")
        if not session_id:
            return JSONResponse({"success": False, "error": "Non connecté"}, status_code=401)
        
        account_info = get_account_by_session(session_id)
        if not account_info:
            return JSONResponse({"success": False, "error": "Compte non trouvé"}, status_code=401)
        
        fights = get_player_fights(account_info["account_id"], limit=min(limit, 100))
        
        return JSONResponse({
            "success": True,
            "fights": fights,
            "total": len(fights)
        })
        
    except Exception as e:
        logger.error(f"Get fights error: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


# ==================== GUILD STATS ENDPOINTS ====================

@router.get("/guild/{guild_id}/stats")
async def get_guild_statistics(request: Request, guild_id: str):
    """Get statistics for a guild"""
    try:
        session_id = request.cookies.get("session_id")
        api_key = get_api_key_by_session(session_id) if session_id else None
        
        # Get guild info from API
        guild_info = await gw2_api.get_guild_info(guild_id, api_key)
        
        # Get aggregated stats
        stats = get_guild_stats(guild_id)
        
        if not stats and not guild_info:
            return JSONResponse({
                "success": False,
                "error": "Guilde non trouvée"
            }, status_code=404)
        
        return JSONResponse({
            "success": True,
            "guild_info": guild_info,
            "stats": stats.to_dict() if stats else None
        })
        
    except Exception as e:
        logger.error(f"Get guild stats error: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.get("/guilds")
async def get_my_guilds(request: Request):
    """Get guilds for connected account"""
    try:
        session_id = request.cookies.get("session_id")
        if not session_id:
            return JSONResponse({"success": False, "error": "Non connecté"}, status_code=401)
        
        api_key = get_api_key_by_session(session_id)
        if not api_key:
            return JSONResponse({"success": False, "error": "Clé API non trouvée"}, status_code=401)
        
        account = await gw2_api.get_account(api_key)
        if not account:
            return JSONResponse({"success": False, "error": "Compte non trouvé"}, status_code=401)
        
        # Get guild details for each guild
        guilds = []
        for guild_id in account.guilds[:5]:  # Limit to 5 guilds
            guild_info = await gw2_api.get_guild_info(guild_id, api_key)
            if guild_info:
                # Get stats if available
                stats = get_guild_stats(guild_id)
                guilds.append({
                    "id": guild_id,
                    "name": guild_info.get("name", "Unknown"),
                    "tag": guild_info.get("tag", ""),
                    "has_stats": stats is not None,
                    "fight_count": stats.total_fights if stats else 0
                })
        
        return JSONResponse({
            "success": True,
            "guilds": guilds
        })
        
    except Exception as e:
        logger.error(f"Get guilds error: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


# ==================== HISTORY PAGE ====================

@router.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    """Fight history page"""
    session_id = request.cookies.get("session_id")
    connected = False
    account_info = None
    career_stats = None
    spec_stats = None
    recent_fights = []
    
    if session_id:
        api_key = get_api_key_by_session(session_id)
        if api_key:
            account = await gw2_api.get_account(api_key)
            if account:
                connected = True
                account_info = account.to_dict()
                
                # Get stats
                career_stats = get_player_career_stats(account.account_id)
                spec_stats = get_player_spec_stats(account.account_id)
                recent_fights = get_player_fights(account.account_id, limit=20)
    
    lang = request.cookies.get("lang", "fr")
    
    return templates.TemplateResponse(
        "history.html",
        {
            "request": request,
            "connected": connected,
            "account": account_info,
            "career_stats": career_stats.to_dict() if career_stats else None,
            "spec_stats": spec_stats,
            "recent_fights": recent_fights,
            "lang": lang
        }
    )
