import json

from telegram import InlineKeyboardButton

import emojis


class XOGame:
    def __init__(self, game_id: str, player1: dict, player2: dict = None) -> None:
        self.game_id = game_id
        self.player1 = player1
        self.player2 = player2
        self.winner = None
        self.winner_keys = []
        self.whose_turn = True  # True: Player1, False: Player2
        self.board = [
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
        ]
        self.board_keys = [
            [InlineKeyboardButton(
                ".",
                callback_data=json.dumps({"type": "K", "coord": [i, j], "end": False}),
            ) for j in range(3)]
            for i in range(3)
        ]

    def is_draw(self) -> bool:
        for i in range(3):
            for j in range(3):
                if not self.board[i][j]:
                    return False

        new_board_keys = []
        for i in range(3):
            row = []
            for j in range(3):
                if self.board[i][j] == 0:
                    label = "."
                elif self.board[i][j] == 1:
                    label = emojis.X_loser
                else:
                    label = emojis.O_loser
                row.append(InlineKeyboardButton(
                    label,
                    callback_data=json.dumps({"type": "K", "coord": [i, j], "end": True}),
                ))
            new_board_keys.append(row)

        new_board_keys.append([InlineKeyboardButton(
            "Play again!",
            callback_data=json.dumps({"type": "R"}),
        )])
        self.board_keys = new_board_keys
        return True

    def fill_board(self, player_id: int, coord) -> bool:
        i, j = coord[0], coord[1]
        if self.board[i][j]:
            return False

        if player_id == self.player1["id"]:
            self.board[i][j] = 1
            label = emojis.X
        else:
            self.board[i][j] = 2
            label = emojis.O

        self.board_keys[i][j] = InlineKeyboardButton(
            label,
            callback_data=json.dumps({"type": "K", "coord": [i, j], "end": False}),
        )
        return True

    def check_winner(self) -> bool:
        b = self.board
        if b[0][0] == b[0][1] == b[0][2] != 0:
            self.winner = self.player1 if b[0][0] == 1 else self.player2
            self.winner_keys.extend([(0, 0), (0, 1), (0, 2)])
        elif b[0][0] == b[1][0] == b[2][0] != 0:
            self.winner = self.player1 if b[0][0] == 1 else self.player2
            self.winner_keys.extend([(0, 0), (1, 0), (2, 0)])
        elif b[0][0] == b[1][1] == b[2][2] != 0:
            self.winner = self.player1 if b[0][0] == 1 else self.player2
            self.winner_keys.extend([(0, 0), (1, 1), (2, 2)])
        elif b[1][0] == b[1][1] == b[1][2] != 0:
            self.winner = self.player1 if b[1][1] == 1 else self.player2
            self.winner_keys.extend([(1, 0), (1, 1), (1, 2)])
        elif b[0][1] == b[1][1] == b[2][1] != 0:
            self.winner = self.player1 if b[1][1] == 1 else self.player2
            self.winner_keys.extend([(0, 1), (1, 1), (2, 1)])
        elif b[0][2] == b[1][1] == b[2][0] != 0:
            self.winner = self.player1 if b[1][1] == 1 else self.player2
            self.winner_keys.extend([(0, 2), (1, 1), (2, 0)])
        elif b[2][0] == b[2][1] == b[2][2] != 0:
            self.winner = self.player1 if b[2][2] == 1 else self.player2
            self.winner_keys.extend([(2, 0), (2, 1), (2, 2)])
        elif b[0][2] == b[1][2] == b[2][2] != 0:
            self.winner = self.player1 if b[2][2] == 1 else self.player2
            self.winner_keys.extend([(0, 2), (1, 2), (2, 2)])

        if not self.winner:
            return False

        new_board_keys = []
        for i in range(3):
            row = []
            for j in range(3):
                if b[i][j] == 0:
                    label = "."
                elif b[i][j] == 1:
                    label = (emojis.X if self.player1["id"] == self.winner["id"]
                             and (i, j) in self.winner_keys else emojis.X_loser)
                else:
                    label = (emojis.O if self.player2["id"] == self.winner["id"]
                             and (i, j) in self.winner_keys else emojis.O_loser)
                row.append(InlineKeyboardButton(
                    label,
                    callback_data=json.dumps({"type": "K", "coord": [i, j], "end": True}),
                ))
            new_board_keys.append(row)

        new_board_keys.append([InlineKeyboardButton(
            "Play again!",
            callback_data=json.dumps({"type": "R"}),
        )])
        self.board_keys = new_board_keys
        return True
