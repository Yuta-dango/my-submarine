import json
import itertools
import seaborn as sns
import matplotlib.pyplot as plt
import sys
import os

sys.path.append(os.getcwd())
from hirotalib.util import near


# 自分と敵が得ている情報(海図)を管理するクラス
class Chart:
    FIELD_SIZE = 5
    SHIPS = ["w", "c", "s"]
    PLAYERS = ["me", "enemy"]

    # ありうる初期状態を全て列挙する。分布は一様であると仮定する。
    def __init__(self, position):
        self.charts = {p: [] for p in Chart.PLAYERS}
        coordinates = [
            (x, y) for x in range(Chart.FIELD_SIZE) for y in range(Chart.FIELD_SIZE)
        ]
        for w, c, s in itertools.permutations(coordinates, 3):
            for p in Chart.PLAYERS:
                self.charts[p].append({"w": w, "c": c, "s": s})
        self.hps = {p: {"w": 3, "c": 2, "s": 1} for p in Chart.PLAYERS}
        self.my_position = position

    # 移動した側の海図を更新する。
    def mover_update(self, player, ship, distance):
        new_charts = []
        for chart in self.charts[player]:
            x = chart[ship][0] + distance[0]  # 進んだ先の座標
            y = chart[ship][1] + distance[1]
            # はみ出さないかチェック
            if 0 <= x < Chart.FIELD_SIZE and 0 <= y < Chart.FIELD_SIZE:
                # 他の敵艦と衝突しないかチェック
                ok = True
                for pos in chart.values():
                    if pos == (x, y):
                        ok = False
                        break
                if ok:
                    # 敵艦の位置を更新する。
                    chart[ship] = (x, y)
                    new_charts.append(chart)
        self.charts[player] = new_charts

    # 攻撃した側の海図を更新する。
    def attacker_update(self, player, position):
        new_charts = []
        for chart in self.charts[player]:
            for pos in chart.values():
                # 撃った位置の近傍にいずれかの攻撃側艦がいればよい
                if near(pos, position):
                    new_charts.append(chart)
                    break
        self.charts[player] = new_charts

    # 攻撃された側の海図を更新する。
    def attacked_update(self, player, position, hit, near_list):
        new_charts = []
        for chart in self.charts[player]:
            ok = True
            # 命中した場合
            if hit is not None:
                # 命中した位置に該当する艦がいなければ矛盾
                if chart[hit] != tuple(position):
                    ok = False
                # 撃沈した場合は海図から削除する。
                elif self.hps[player][hit] == 1:
                    del chart[hit]
            # 命中しなかった場合
            else:
                # 撃った位置に艦がいれば矛盾
                for pos in chart.values():
                    if pos == tuple(position):
                        ok = False
                        break
                # near_listとの整合性を確認する。
                for ship in chart.keys():
                    if (ship in near_list) != near(chart[ship], position):
                        ok = False
                        break
            if ok:
                new_charts.append(chart)
        self.charts[player] = new_charts

    def hp_update(self, player, condition):
        for ship in self.hps[player].keys():
            if ship in condition:
                self.hps[player][ship] = condition[ship]["hp"]
            else:
                self.hps[player][ship] = 0

    # プレイヤーの手番に通知された情報で状態を更新する。
    def player_update(self, json_):
        if "result" in json.loads(json_):
            result = json.loads(json_)["result"]
            # 攻撃した場合
            if "attacked" in result:
                attacked = result["attacked"]
                position = attacked["position"]
                hit = attacked["hit"] if "hit" in attacked else None
                near = attacked["near"] if "near" in attacked else []
                # 自分の海図を更新
                self.attacker_update("me", position)
                # 敵の海図を更新
                self.attacked_update("enemy", position, hit, near)
        # 移動した場合
        my_condition = json.loads(json_)["condition"]["me"]
        for ship, hp in self.hps["me"].items():
            if hp == 0:
                continue
            prev = self.my_position[ship]
            new = my_condition[ship]["position"]
            if prev != new:
                distance = [new[0] - prev[0], new[1] - prev[1]]
                self.mover_update("me", ship, distance)
                self.my_position[ship] = new
                break
        # 敵のhpを更新
        enemy_condition = json.loads(json_)["condition"]["enemy"]
        self.hp_update("enemy", enemy_condition)

    # 相手の手番に通知された情報で状態を更新する。
    def enemy_update(self, json_):
        if "result" in json.loads(json_):
            result = json.loads(json_)["result"]
            # 攻撃された場合
            if "attacked" in result:
                attacked = result["attacked"]
                position = attacked["position"]
                hit = attacked["hit"] if "hit" in attacked else None
                near = attacked["near"] if "near" in attacked else []
                # 自分の海図を更新
                self.attacked_update("me", position, hit, near)
                # 敵の海図を更新
                self.attacker_update("enemy", position)
            # 移動された場合
            if "moved" in result:
                ship = result["moved"]["ship"]
                distance = result["moved"]["distance"]
                self.mover_update("enemy", ship, distance)
        # 味方のhpを更新
        my_condition = json.loads(json_)["condition"]["me"]
        self.hp_update("me", my_condition)

    def info(self, visualize=0):
        # ある艦がそれぞれのマスにいる確率
        ship_probs = {
            p: {
                ship: [
                    [0 for _ in range(Chart.FIELD_SIZE)]
                    for _ in range(Chart.FIELD_SIZE)
                ]
                for ship in Chart.SHIPS
            }
            for p in Chart.PLAYERS
        }
        # それぞれのマスを撃ちたい度合い
        score = [[0 for _ in range(Chart.FIELD_SIZE)] for _ in range(Chart.FIELD_SIZE)]
        # それぞれのマスが敵の射程内である確率
        enemy_range = [
            [0 for _ in range(Chart.FIELD_SIZE)] for _ in range(Chart.FIELD_SIZE)
        ]
        for player in Chart.PLAYERS:
            for chart in self.charts[player]:
                for ship, pos in chart.items():
                    ship_probs[player][ship][pos[0]][pos[1]] += 1
                    if player == "enemy":
                        # 頭数を減らしたほうが有利だと思われるので、確率をhpで割る。
                        score[pos[0]][pos[1]] += 1 / self.hps["enemy"][ship]
                if player == "enemy":
                    for x in range(Chart.FIELD_SIZE):
                        for y in range(Chart.FIELD_SIZE):
                            for pos in chart.values():
                                if near([x, y], pos):
                                    enemy_range[x][y] += 1
                                    break
        for player in Chart.PLAYERS:
            n = len(self.charts[player])
            for x in range(Chart.FIELD_SIZE):
                for y in range(Chart.FIELD_SIZE):
                    for ship in Chart.SHIPS:
                        ship_probs[player][ship][x][y] /= n
                    if player == "enemy":
                        score[x][y] /= n
                        enemy_range[x][y] /= n

        def plot_hm(data, color):
            sns.heatmap(
                [list(x) for x in zip(*data)],
                annot=True,
                cbar=False,
                cmap=color,
                vmin=0,
                vmax=1,
            )

        if visualize:
            plt.figure(figsize=(9, 9))
            plt.subplots_adjust(wspace=0.2, hspace=0.3)
            r, c = 3, 3
            plt.subplot(r, c, 1)
            plot_hm(ship_probs["enemy"]["w"], "Reds")
            plt.title("warship")
            plt.subplot(r, c, 2)
            plot_hm(ship_probs["enemy"]["c"], "Reds")
            plt.title("cruiser")
            plt.subplot(r, c, 3)
            plot_hm(ship_probs["enemy"]["s"], "Reds")
            plt.title("submarine")
            plt.subplot(r, c, 4)
            plot_hm(score, "Reds")
            plt.title("score")
            plt.subplot(r, c, 5)
            plot_hm(enemy_range, "Reds")
            plt.title("enemy range")
            plt.subplot(r, c, 7)
            plot_hm(ship_probs["me"]["w"], "Blues")
            plt.title("warship")
            plt.subplot(r, c, 8)
            plot_hm(ship_probs["me"]["c"], "Blues")
            plt.title("cruiser")
            plt.subplot(r, c, 9)
            plot_hm(ship_probs["me"]["s"], "Blues")
            plt.title("submarine")
            plt.show()
        return ship_probs, score, enemy_range
