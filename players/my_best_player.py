import json
import os
import random
import socket
import sys
import pandas as pd
import numpy as np

sys.path.append("/Users/hashiguchiyutaka/Desktop/3S/prog/submarine-py")

from lib.make_coordinates import *
from lib.player_base import Player, PlayerShip

# パラメータ
# これらの値を変えて自己対戦し、強いと思われる値を探した
# 各パラメータの説明は、MyPlayerのaction関数内に記載

if_attacked_move = 0.3
# 0.4 > 0.8
# 0.5 > 0.2
# 0.3 > 0.4

attack_or_move = 0.1
# 0.1 > 0.4
# 0.1 > 0.2
# 0.1 > 0.01

for_now_or_future = 0.1
# 0.2 > 0.5
# 0.1 > 0.15 = attack_or_move


class Enemy:
    """
    敵の盤面を管理するクラス
    """
    def __init__(self):
        # 可能性のあるすべての盤面を持つdataframe. 盤面の全パターンを初期値に
        self.df = pd.DataFrame(make_all_coordinates()) 
        self.ships = ["w", "c", "s"]

    def remove_same_position(self):
        """
        self.ships内の船の位置が重複している行を削除する
        残った船の盤面に重複がある可能性があるが、確率を考える上では問題ない
        """
        # 船が1つしかなければ重複はない
        if len(self.ships) == 1:
            pass
        elif len(self.ships) == 2:
            self.df = self.df[self.df.apply(lambda x: x[self.ships[0]] != x[self.ships[1]], axis=1)]
        else:
            self.df = self.df[self.df.apply(lambda x: x["w"] != x["c"] and x["w"] != x["s"] and x["c"] != x["s"], axis=1)]

    def move(self, ship_type: str, direction: list) -> None:
        """
        args:
            ship_type: str (船の種類)
            direction: list([1,0]などの移動分を表す)
        敵のmoveを処理し、self.dfを更新
        
        self.df.loc[:, ship_type]を使うことでSettingWithCopyWarningをさけ、確実に元のdfを変更できるようにする
        """
        delta_x = direction[0]
        delta_y = direction[1]
        self.df.loc[:, ship_type] = self.df[ship_type].map(lambda x: (x[0] + delta_x , x[1] + delta_y))
        
        # 有効な座標以外の盤面を削除
        self.df = self.df[self.df[ship_type].map(lambda x: x in valid_coordinates())]

        # 座標がダブっている船を含む盤面を削除(移動によりダブってしまうような盤面は存在し得ない)
        self.remove_same_position()
    
    def attack(self, position: list) -> None:
        """
        args:
            position: list (敵が攻撃した座標)
        敵のattackを処理し、self.dfを更新
        (positionの周囲1マス(自身を含む)にいずれかの敵がいることが確定する)
        """
        # positionの周囲1マス(自身を含む)の座標
        near_positions = all_nears(position, me=True)

        # self.dfの中から、near_positionsに含まれる座標がある行のみを残す

        # self.dfの行が、near_positionsに含まれる座標を持つかどうかを判定する関数
        def is_valid(x): # xはself.dfの行
            for ship in self.ships:
                if x[ship] in near_positions:
                    return True
            # どの船もnear_positionsに含まれる座標を持っていない場合
            return False
            
        self.df = self.df[self.df.apply(is_valid, axis=1)]

    def hit(self, ship_type: str, position: list) -> None:
        """
        自分の攻撃がhitして、かつその船がまだ生きている時の処理
        args:
            ship_type: str (hitした船の種類)
            position: list (hitした座標)
        """
        coordinate = tuple(position) # 忘れずに
        self.df = self.df[self.df[ship_type] == coordinate]
        # print(self.prob()) (hit関数が動いているなら、ここを表示すると常に確率1の座標が存在するはず)

    def miss(self, position) -> None:
        """
        自分の攻撃がmissした時の処理
        """
        # 結局、near/not_nearで処理するので何もしない
        pass

    def near(self, ship_type: str, position: list) -> None:
        """
        自分の攻撃の結果、ship_typeがnearにいた時の処理
        positionの周囲1マス(自身を含まない)にその船がいることが確定する
        """
        coordinate = tuple(position)
        # near_positionsはpositionの周囲1マス(自身を含まない)の座標
        near_positions = all_nears(coordinate, me=False)
        self.df = self.df[self.df[ship_type].map(lambda x: x in near_positions)]

    def not_near(self, ship_type: str, position: list) -> None:
        """ 
        自分の攻撃の結果、ship_typeがnot_nearだった時の処理
        positionの周囲1マス(自身を含む)以外のマスにその船がいることが確定する
        """
        coordinate = tuple(position)
        # near_positionsはpositionの周囲1マス(自身を含む)の座標
        near_positions = all_nears(coordinate, me=True)
        self.df = self.df[self.df[ship_type].map(lambda x: x not in near_positions)]

    def prob(self) -> pd.Series:
        """
        return:
            self.dfを各座標の確率分布に変換したseries
        """
        return self.df.stack().value_counts()/len(self.df)
    
    def safe_position(self) -> set:
        """
        return:
            相手の船が絶対にいない座標(tuple)の集合
        """
        not_safe = set() # {}とするとdictになるので注意
        for coordinate in self.prob().keys():
            # 相手がいる可能性のある座標の周囲1マス(自身を含む)の座標をnot_safeに追加
            not_safe |= all_nears(coordinate, me=True)

        # valid_coordinates()からnot_safeを引いたものが安全な座標
        return valid_coordinates() - not_safe # setの差集合
    
    def where_to_attack(self) -> list:
        """
        return:
            相手のいる確率高い座標(tuple)を順に並べたlist
            [(4, 2),(4, 0),...]
        """
        return [coordinate for coordinate in self.prob().keys()]
    

class MyPlayer(Player):

    def __init__(self):

        # フィールドを2x2の配列として持っている．
        self.field = [[i, j] for i in range(Player.FIELD_SIZE)
                      for j in range(Player.FIELD_SIZE)]

        # 敵の盤面を管理するEnemyクラスのインスタンスを持たせる
        self.enemy = Enemy()

        # 直近で攻撃された船を記録
        self.damaged_ship = None

        # リストmake_not_near_coordinates()に存在する盤面の中からランダムに1つ選ぶ．
        positions = random.choice(make_not_near_coordinates())
        super().__init__(positions) # self.shipsが設定される


    def action(self) -> str: # json形式
        """
        行動の前にself.enemy.prob()、つまり相手の確率分布を更新
        """
        # 可視化しやすいように、敵の盤面の確率を表示
        print(self.enemy.prob())

        # 敵がいる確率が最も高い座標とその確率を求めておく
        best_position = self.enemy.where_to_attack()[0] # self.enemy.prob().idxmax()でも同じ
        best_prob = self.enemy.prob()[best_position]

        # 攻撃可能な座標のうち、確率が最も高い座標を探す
        attackable_prob = None # UnboundLocalErrorを避けるためにNoneで初期化
        for position in self.enemy.where_to_attack():
            if self.can_attack(position):
                attackable_prob = self.enemy.prob()[position]
                break
        
        ########行動1: 直近で攻撃されたとき、攻撃があたる見込みが低く、かつself.damaged_shipが安全なマスに移動できるなら移動########
        if self.damaged_ship:
            if not self.damaged_ship in self.ships.values():
                pass

            # attackable_probが一定以上なら行動1は選択しない
            elif attackable_prob > if_attacked_move: 
                pass
            else:
                safes = []
                for position in self.enemy.safe_position():
                    if self.damaged_ship.can_reach(position) and self.overlap(position) is None:
                        safes.append(position)
                if safes: # 安全なマスに移動できる場合
                    # safesの中で、自分の位置との距離が最も近いマスに移動する
                    to = min(safes, key=lambda x: distance(x, self.damaged_ship.position)) 
                    to = list(to)
                    
                    print(f"行動1・move: {self.damaged_ship.type, to}")
                    return json.dumps(self.move(self.damaged_ship.type, to)) # dict -> JSON形式の文字列

        ########行動2: 自分の船が1つしか生き残ってない時########
        if len(self.ships) == 1:
            ship = list(self.ships.values())[0] # 唯一の船

            # 確実に攻撃できるわけではなく、かつ自分の今いる場所が自分の今いる場所が安全なら
            if attackable_prob != 1 and tuple(ship.position) in self.enemy.safe_position():
                to = ship.position
                print(f"行動2・attack: {to}")
                return json.dumps(self.attack(to)) # dict -> JSON形式の文字列
                

        ########行動3: 攻撃可能なマスのうち最も相手がいる確率の高いマスを攻撃する########
        #
        # attackable_probが、best_probのattack_or_move倍以上なら攻撃する
        #

        # attackable_probが、best_probのattack_or_move倍以上 である場合
        if attackable_prob and attackable_prob >= attack_or_move * best_prob: # short circuit

            # self.enemy.prob()のうち、valueがattackable_probであり、かつ攻撃可能な座標を列挙
            attackable_positions = {position for position in self.enemy.where_to_attack() if self.can_attack(position) and self.enemy.prob()[position] == attackable_prob}
            
            attackable_center_positions = attackable_positions & center_coordinates() 
            attackable_side_positions = attackable_positions & side_coordinates()
            attackable_corner_positions = attackable_positions & corner_coordinates()

            # 攻撃可能な座標のうち、中心に近い(辺に面してない)座標が存在するならそこからランダムに選ぶ
            if attackable_center_positions: 
                to = random.choice(list(attackable_center_positions))

            # 攻撃可能な座標のうち、辺上の座標が存在するならそこからランダムに選ぶ
            elif attackable_side_positions:
                to = random.choice(list(attackable_side_positions))

            # それもない場合、角からランダムに選ぶ
            else:
                to = random.choice(list(attackable_corner_positions))
            to = list(to) # tuple -> list
            print(f"行動3・attack: {to}")
            return json.dumps(self.attack(to)) # dict -> JSON形式の文字列

        ########行動4: 相手の船が存在する可能性があるマスの周囲へ移動########
        #
        # 行動3を取らなかったということは、今ターンで攻撃する価値がないと判断し、次ターンで攻撃しやすくするために移動をする
        #

        for coordinate in self.enemy.where_to_attack(): # 敵の盤面の確率が高い座標から順に(early returnする)
            
            # coordinate の確率がbest_probのor_now_or_future倍より小さいなら、そのマスを目指す価値はない
            # 「攻撃するのは確率が低いからやめたマス」の周りに移動するみたいなことが起こらないよう、for_now_or_futureはattack_or_move以上でなくてはならない
            assert for_now_or_future >= attack_or_move
            if self.enemy.prob()[coordinate] < for_now_or_future * best_prob:
                break

            # coordinateの周囲1マス(自身を含む)のうち、移動可能なマスを列挙
            to_candidate = {} # {(x, y): そこにいけるshipオブジェクト} のdict
            for position in all_nears(coordinate, me=True): 
                for ship in self.ships.values(): # shipオブジェクトについて回す
                    if ship.can_reach(position) and self.overlap(position) is None:
                        to_candidate[position] = ship 

            # to_candidateが空でないなら、このcoordinateの周辺に移動可能なので移動する
            # ただし、周辺マスのうち、現在の自分の位置との距離が最も近いマスに移動する
            if to_candidate: 
                to = min(list(to_candidate.keys()), key=lambda x: distance(x, to_candidate[x].position)) # to_candidate[x]はshipオブジェクト。hpが最も低い船を選ぶ 
                
                ship = to_candidate[to]    
                to = list(to) # tuple -> list
                print(f"行動4・move: {ship.type, to}")
                return json.dumps(self.move(ship.type, to)) # dict -> JSON形式の文字列
        
        #######行動5: それでも無理なら、相手がいる可能性が最も高いマスに片方の座標を合わせる######

        # hpが最も低い船を選ぶ
        # ここでもmin関数のkey引数を使う
        ship = max(self.ships.values(), key=lambda x: x.hp)
        
        # 相手が存在する確率が最も高い座標
        target = self.enemy.prob().idxmax() # idxmax()はvalueが最も大きいindexを返す

        # targetの片方の座標をship.positionのx座標に合わせる
        # この位置は、確実に到達できるし、自分の他の船がいることもない
        to = list(make_near_x_or_y(ship.position, best_position)) 

        print(f"行動5・move: {ship.type, to}")
        return json.dumps(self.move(ship.type, to))

    def update(self, json_):
        """
        自分と相手それぞれの'condition'を更新する。
        自分のターンでも相手のターンでも実行する
        """
        super().update(json_) # 親クラスのupdateメソッドを呼び出す(=自分の状態を更新)

        # 相手の船の存在状況を更新
        cond_e = json.loads(json_)['condition']['enemy'] # {"w":{"hp":1},"s":{"hp":1}}

        # 相手の船が存在するか否かを更新
        self.enemy.ships = list(cond_e.keys()) # like ["w", "c"]

        # 存在しない船についてはdataframeからカラムを削除する
        self.enemy.df = self.enemy.df[self.enemy.ships]

    def enemy_update(self, json_):
        """
        相手のターンに、相手の行動結果(result)を処理
        """
        self.damaged_ship = None # 直近で攻撃された船をリセット
        result = json.loads(json_)['result']

        # {"moved":{"ship":"w","distance":[0,-2]}}を捉えて処理
        if "moved" in result:
            # 動いた船と方向を入れて、self.enemy.dfを更新する
            self.enemy.move(result["moved"]["ship"], result["moved"]["distance"])

        # {"attacked":{"position":[4,2],"hit":"s","near":["w"]}}を捉えて処理
        # このうち、"position"のみ使う(敵がどこを攻撃したかで敵の位置が絞れる)
        if "attacked" in result:
            # 攻撃された座標を取得し、self.enemy.dfを更新する
            attacked_position = result["attacked"]["position"]
            self.enemy.attack(attacked_position)

            # ヒットされた時
            if "hit" in result["attacked"]:
                # ヒットされた自分の船がまだ生きている場合
                if result["attacked"]["hit"] in self.ships:
                    self.damaged_ship = self.ships[result["attacked"]["hit"]] # 直近で攻撃された船を記録

    def my_update(self,json_):
        """
        自分のターンでは、自分の行動結果(result)を処理 (= 攻撃した時のnearやhitの情報)
        自分の行動がmoveの場合はresultが返ってこない。この場合は何もしない
        """
        if "result" in json.loads(json_): # 自分の行動がattackの場合
            result = json.loads(json_)['result']["attacked"]

            # {"attacked":{"position":[4,2],"hit":"s","near":["w"]}}を捉えて処理
            # ヒットしていた時
            if "hit" in result:
                # ヒットした船がまだ生きている場合
                if result["hit"] in self.enemy.ships:
                    self.enemy.hit(result["hit"], result["position"]) # (船の種類,座標)

            # ヒットしていなかった時の処理は、nearとnot_nearで処理するので不要
            
            # それぞれの船が、nearに含まれているか否かを反映させる
            for ship in self.enemy.ships: # self.enemy.ships is like ["w", "c"]
                # ヒットした船については処理済みなのでスキップ
                if "hit" in result:
                    if ship == result["hit"]: 
                        continue
                if ship in result["near"]:
                    self.enemy.near(ship, result["position"])
                else:
                    self.enemy.not_near(ship, result["position"])

# 仕様に従ってサーバとソケット通信を行う．
def main(host, port, seed=0):
    assert isinstance(host, str) and isinstance(port, int)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((host, port))
        completed = False
        with sock.makefile(mode="rw", buffering=1) as sockfile:
            while True:
                get_msg = sockfile.readline()
                print(get_msg)
                player = MyPlayer()
                sockfile.write(player.initial_condition() + "\n")

                while True:
                    info = sockfile.readline().rstrip()
                    print(info)
                    if info == "your turn":
                        sockfile.write(player.action() + "\n")
                        get_msg = sockfile.readline()
                        player.update(get_msg)
                        player.my_update(get_msg)

                    elif info == "waiting":
                        get_msg = sockfile.readline()
                        player.update(get_msg)
                        player.enemy_update(get_msg)
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
                    print()
                    for _ in range(5):
                        info = sockfile.readline()
                        print(info, end="")
                    break

if __name__ == '__main__':
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
    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed of the player",
        required=False,
        default=0,
    )
    args = parser.parse_args()

    main(args.host, args.port, seed=args.seed)