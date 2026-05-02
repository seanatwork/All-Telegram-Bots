from collections import OrderedDict

from XOGameObject import XOGame

MAX_GAMES = 100
games: "OrderedDict[str, XOGame]" = OrderedDict()


def get_game(game_id: str, data: dict):
    """Return the game for `game_id`, creating it from a Player-accept payload.

    Returns None if no such game exists and `data` isn't a player-accept
    (so callbacks against forgotten games surface as "expired" instead of crashing).
    """
    if game_id in games:
        games.move_to_end(game_id)
        return games[game_id]

    if data.get("type") == "P" and "id" in data and "name" in data:
        if len(games) >= MAX_GAMES:
            games.popitem(last=False)
        game = XOGame(game_id, data)
        games[game_id] = game
        return game

    return None


def remove_game(game_id: str) -> bool:
    return games.pop(game_id, None) is not None


def reset_game(game: XOGame):
    """Swap player order and start a fresh game under the same inline_message_id."""
    game_id = game.game_id
    new_p1 = game.player2
    new_p2 = game.player1
    if not remove_game(game_id):
        return None
    new_game = XOGame(game_id, new_p1, new_p2)
    games[game_id] = new_game
    return new_game
