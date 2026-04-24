"""MLB.com video highlights using MLB Stats API."""
import asyncio
import time
import requests
from datetime import date, timedelta
from typing import Optional, List, Dict, Tuple

from logger import get_logger
from wshnats_config import NATIONALS_TEAM_ID

logger = get_logger(__name__)

# Cache
_cache: dict[str, tuple[float, object]] = {}
_TTL_HIGHLIGHTS = 300  # 5 minutes

def _get_cached(key: str, ttl: float):
    """Return cached value if still fresh, else None."""
    entry = _cache.get(key)
    if entry and (time.monotonic() - entry[0]) < ttl:
        return entry[1]
    return None

def _set_cached(key: str, value) -> None:
    _cache[key] = (time.monotonic(), value)

def _pick_best_highlight(items: list) -> Optional[dict]:
    """Return the most Nationals-relevant highlight from a game's item list."""
    # Prefer: game recap that isn't a condensed-game clip
    for item in items:
        kws = {kw.get('value') for kw in item.get('keywordsAll', [])}
        title = item.get('headline', '')
        if ('mlb_recap' in kws or 'game-recap' in kws) and 'Condensed' not in title:
            return item
    # Then: any Nationals-tagged non-condensed clip
    for item in items:
        kws = {kw.get('value') for kw in item.get('keywordsAll', [])}
        if 'teamid-120' in kws and 'Condensed' not in item.get('headline', ''):
            return item
    # Fallback: first non-condensed item
    for item in items:
        if 'Condensed' not in item.get('headline', ''):
            return item
    return items[0] if items else None


def _thumbnail_url(item: dict, target_width: int = 640) -> Optional[str]:
    """Return the image URL closest to target_width at 16:9."""
    cuts = item.get('image', {}).get('cuts', [])
    candidates = [c for c in cuts if c.get('aspectRatio') == '16:9'] or cuts
    if not candidates:
        return None
    return min(candidates, key=lambda c: abs(c['width'] - target_width))['src']


def _fetch_weekly_thumbnails_sync() -> List[Tuple[str, bytes]]:
    """Blocking: one thumbnail per Nationals game over the past 7 days."""
    base_url = "https://statsapi.mlb.com/api/v1"
    today = date.today()
    week_ago = today - timedelta(days=7)

    resp = requests.get(f"{base_url}/schedule", params={
        "sportId": 1, "teamId": NATIONALS_TEAM_ID,
        "startDate": week_ago.strftime("%Y-%m-%d"),
        "endDate": today.strftime("%Y-%m-%d"),
        "gameType": "R",
        "fields": "dates,games,gamePk,status,abstractGameState",
    }, timeout=15)
    resp.raise_for_status()

    game_ids = []
    for date_entry in resp.json().get('dates', []):
        for game in date_entry.get('games', []):
            if game.get('status', {}).get('abstractGameState') == 'Final':
                game_ids.append(game['gamePk'])

    results: List[Tuple[str, bytes]] = []
    for gid in game_ids[-9:]:  # at most 9 for a 3×3 grid
        try:
            content = requests.get(f"{base_url}/game/{gid}/content", timeout=10).json()
            items = content.get('highlights', {}).get('highlights', {}).get('items', [])
            if not items:
                continue
            pick = _pick_best_highlight(items)
            if not pick:
                continue
            url = _thumbnail_url(pick, target_width=640)
            if not url:
                continue
            img_resp = requests.get(url, timeout=10)
            img_resp.raise_for_status()
            results.append((pick.get('headline', 'Highlight'), img_resp.content))
        except Exception as e:
            logger.debug(f"Skipping game {gid} thumbnail: {e}")
    return results


async def get_weekly_highlight_thumbnails() -> List[Tuple[str, bytes]]:
    """Async wrapper — returns list of (headline, jpeg_bytes) for the past week."""
    cache_key = f"weekly_thumbs_{date.today()}"
    cached = _get_cached(cache_key, 3600)
    if cached is not None:
        return cached
    result = await asyncio.to_thread(_fetch_weekly_thumbnails_sync)
    _set_cached(cache_key, result)
    return result


async def get_nationals_highlights() -> Optional[str]:
    """Get 3 most recent Washington Nationals highlights from MLB.com."""
    cache_key = f"highlights_{date.today()}"
    cached = _get_cached(cache_key, _TTL_HIGHLIGHTS)
    if cached is not None:
        return cached
    
    try:
        highlights = []
        
        # Try to get highlights from recent games
        base_url = "https://statsapi.mlb.com/api/v1"
        
        # First, get recent Nationals games
        today = date.today()
        last_week = today - timedelta(days=7)
        
        schedule_params = {
            "sportId": 1,
            "teamId": NATIONALS_TEAM_ID,
            "startDate": last_week.strftime("%Y-%m-%d"),
            "endDate": today.strftime("%Y-%m-%d"),
            "gameType": "R",
            "fields": "dates,games,gamePk,gameDate,status,abstractGameState,teams,home,away,team,name"
        }
        
        resp = await asyncio.to_thread(
            requests.get, f"{base_url}/schedule", params=schedule_params, timeout=15
        )
        resp.raise_for_status()
        schedule_data = resp.json()
        
        # Get game IDs for completed games
        game_ids = []
        for date_entry in schedule_data.get('dates', []):
            for game in date_entry.get('games', []):
                status = game.get('status', {})
                if status.get('abstractGameState') in ['Final', 'Live']:
                    game_ids.append(game.get('gamePk'))
        
        # Fetch highlights for each game (most recent first)
        for game_id in reversed(game_ids[-5:]):
            if len(highlights) >= 3:
                break
                
            try:
                content_url = f"{base_url}/game/{game_id}/content"
                content_resp = await asyncio.to_thread(
                    requests.get, content_url, timeout=10
                )
                content_resp.raise_for_status()
                content_data = content_resp.json()
                
                # Get highlights from game content
                for highlight in content_data.get('highlights', {}).get('highlights', {}).get('items', [])[:3]:
                    title = highlight.get('headline', highlight.get('title', 'Highlight'))
                    video_urls = highlight.get('playbacks', [])
                    
                    # Find the best quality MP4 URL
                    video_url = None
                    for playback in video_urls:
                        if playback.get('name') == 'mp4Avc':
                            video_url = playback.get('url')
                            break
                    
                    if not video_url and video_urls:
                        video_url = video_urls[0].get('url')
                    
                    if title and video_url:
                        highlights.append({
                            'title': title,
                            'url': video_url
                        })
                        
                    if len(highlights) >= 3:
                        break
                        
            except Exception as e:
                logger.debug(f"Error fetching highlights for game {game_id}: {e}")
                continue
        
        if not highlights:
            return "No recent Washington Nationals highlights found."
        
        # Format message
        message_lines = ["<b>📺 Recent Washington Nationals Highlights</b>", ""]
        
        for i, highlight in enumerate(highlights[:3], start=1):
            title = highlight['title'][:70] + "..." if len(highlight['title']) > 70 else highlight['title']
            message_lines.append(f"{i}. <a href=\"{highlight['url']}\">{title}</a>")
        
        result = "\n\n".join(message_lines)
        _set_cached(cache_key, result)
        return result
        
    except Exception as e:
        logger.error(f"Error fetching highlights: {e}")
        return "Sorry, couldn't fetch highlights right now. Please try again later."
