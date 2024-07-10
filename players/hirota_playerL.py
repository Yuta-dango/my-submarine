import json
import os
import random
import socket
import sys

sys.path.append(os.getcwd())

from lib.player_base import Player
from hirotalib.chart import Chart
from hirotalib.util import make_initial


class HirotaPlayer(Player):

    def __init__(self):
        # フィールドを2x2の配列として持っている．
        self.field = [
            [i, j] for i in range(Player.FIELD_SIZE) for j in range(Player.FIELD_SIZE)
        ]
        ps = make_initial(self.field)
        positions = {"w": ps[0], "c": ps[1], "s": ps[2]}
        super().__init__(positions)

    def action(self, prob, score, enemy_range, hps):
        # 逃げるかどうか判断する。
        ESCAPE_THRESHOLD = 0.0  # 逃げた先の被弾確率として許容できる上限
        escape_candidate = []  # 逃げ方の候補
        hp_advantage = sum(hps["me"].values()) - sum(
            hps["enemy"].values()
        )  # 合計hpの差
        for ship in self.ships.values():
            pos = ship.position
            # 自分の位置がばれていて、敵の射程内なら検討する
            if (
                prob["me"][ship.type][pos[0]][pos[1]] == 1.0
                and enemy_range[pos[0]][pos[1]] == 1.0
            ):
                min_range_prob = 1.0  # 最も安全なマスにおける、敵の射程内である確率
                confirmed = False  # 自分の射程内に位置の確定している敵艦が存在する
                to = [0, 0]
                for x in range(Player.FIELD_SIZE):
                    for y in range(Player.FIELD_SIZE):
                        if (
                            ship.can_reach([x, y])
                            and self.overlap([x, y]) is None
                            and enemy_range[x][y] < min_range_prob
                        ):
                            to = [x, y]
                            min_range_prob = enemy_range[x][y]
                        if self.can_attack([x, y]):
                            for enemy_ship in ["w", "c", "s"]:
                                if prob["enemy"][enemy_ship][x][y] == 1.0:
                                    confirmed = True
                if (not confirmed and hp_advantage < 1) or hp_advantage < 0:
                    escape_candidate.append([min_range_prob, ship.hp, ship.type, to])
        # 逃げた先の被弾確率が低い逃げ方を優先して採用、同じならhpの低い順に逃がす
        if escape_candidate:
            escape_candidate.sort()
            prob, _, ship_type, to = escape_candidate[0]
            if prob <= ESCAPE_THRESHOLD:
                return json.dumps(self.move(ship_type, to))

        candidate = []  # 攻撃するマスの候補
        max_score = 0  # 射程内におけるスコアの最大値
        for x in range(Player.FIELD_SIZE):
            for y in range(Player.FIELD_SIZE):
                if not self.can_attack([x, y]):
                    continue
                if score[x][y] > max_score:
                    candidate = []
                    max_score = score[x][y]
                if score[x][y] == max_score:
                    candidate.append([x, y])

        # 射程内のスコアが全て0の場合
        if max_score == 0:
            # 自艦隊のhpが敵艦隊以下の場合
            if hp_advantage <= 0:
                # 味方の艦がいる確率が最も高いマスに射撃(不用意に情報を与えないため)
                max_prob = 0
                for x in range(Player.FIELD_SIZE):
                    for y in range(Player.FIELD_SIZE):
                        if not self.can_attack([x, y]):
                            continue
                        prob_sum = sum(
                            [prob["me"][ship][x][y] for ship in self.ships.keys()]
                        )
                        if prob_sum >= max_prob:
                            to = [x, y]
                            max_prob = prob_sum
                return json.dumps(self.attack(to))
            # 自艦隊のhpが敵艦隊より多い場合
            else:
                # スコアが高い位置を目指す
                destination_candidate = []  # 目指す座標の候補
                max_score = 0
                for x in range(Player.FIELD_SIZE):
                    for y in range(Player.FIELD_SIZE):
                        if score[x][y] > max_score:
                            max_score = score[x][y]
                            destination_candidate.append([x, y])
                destination = random.choice(destination_candidate)
                min_dist = Player.FIELD_SIZE * 2
                for ship in self.ships.values():
                    if ship.hp == 0:
                        continue
                    for x in range(Player.FIELD_SIZE):
                        for y in range(Player.FIELD_SIZE):
                            if (
                                not ship.can_reach([x, y])
                                or self.overlap([x, y]) is not None
                            ):
                                continue
                            # destinationとのマンハッタン距離が小さくなるような移動をする
                            distance = abs(destination[0] - x) + abs(destination[1] - y)
                            if distance < min_dist:
                                ship_type = ship.type
                                to = [x, y]
                                min_dist = distance
                return json.dumps(self.move(ship_type, to))

        # 特に問題が無ければスコアの最も高いマス(複数あればランダムに選ぶ)を攻撃する。
        return json.dumps(self.attack(random.choice(candidate)))


# 仕様に従ってサーバとソケット通信を行う．
def main(host, port):
    assert isinstance(host, str) and isinstance(port, int)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((host, port))
        completed = False
        with sock.makefile(mode="rw", buffering=1) as sockfile:
            while True:
                get_msg = sockfile.readline()
                print(get_msg)
                player = HirotaPlayer()
                chart = Chart(
                    {ship: player.ships[ship].position for ship in ["w", "c", "s"]}
                )
                sockfile.write(player.initial_condition() + "\n")

                while True:
                    info = sockfile.readline().rstrip()
                    print(info)
                    if info == "your turn":
                        prob, score, enemy_range = chart.info()
                        sockfile.write(
                            player.action(prob, score, enemy_range, chart.hps) + "\n"
                        )
                        get_msg = sockfile.readline()
                        player.update(get_msg)
                        chart.player_update(get_msg)
                    elif info == "waiting":
                        get_msg = sockfile.readline()
                        player.update(get_msg)
                        chart.enemy_update(get_msg)
                    elif info == "you win":
                        break
                    elif info == "you lose":
                        break
                    elif info == "even":
                        break
                    elif info == "you win.":
                        completed = True
                        break
                    elif info == "you lose.":
                        completed = True
                        break
                    elif info == "even.":
                        completed = True
                        break
                    else:
                        raise RuntimeError("unknown information")
                if completed:
                    for _ in range(5):
                        info = sockfile.readline()
                        print(info, end="")
                    break


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Sample Player for Submaline Game")
    parser.add_argument(
        "host",
        metavar="H",
        type=str,
        help="Hostname of the server. E.g., localhost",
    )
    parser.add_argument(
        "port",
        metavar="P",
        type=int,
        help="Port of the server. E.g., 2000",
    )
    args = parser.parse_args()

    main(args.host, args.port)
