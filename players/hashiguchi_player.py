import json
import os
import random
import socket
import sys
import pandas as pd


sys.path.append("/Users/hashiguchiyutaka/Desktop/3S/prog/submarine-py")

from lib.make_coordinates import make_all_coordinates, valid_coordinates, make_not_near_coordinates
from lib.player_base import Player, PlayerShip


class Enemy:
    def __init__(self):
        self.df = pd.DataFrame(make_all_coordinates()) # 盤面の全パターンを初期値に
        # self.hp = {"w": 3, "c": 2, "s": 1} 相手のhpは今のところ不要では？
        self.ships = ["w", "c", "s"]

    def remove_same_position(self):
        """
        self.ships内の船の位置が重複している行を削除する
        """
        # 船が1つしかなければ重複はない
        if len(self.ships) == 1:
            return None
        elif len(self.ships) == 2:
            self.df = self.df[self.df.apply(lambda x: x[self.ships[0]] != x[self.ships[1]], axis=1)]
        else:
            self.df = self.df[self.df.apply(lambda x: x["w"] != x["c"] and x["w"] != x["s"] and x["c"] != x["s"], axis=1)]

        # 0になったらself.shipsからその船を消す
        # 直接消してしまうと、remove_same_position(self.df)などの実装で不具合があるので、probを求める際に消えている船の座標はカウントしないことにする
        # と思ったけど、こうすると、remove_same_positionで、死んだ船と被っている行動も不可能と見做されてしまう
        # 他の船の位置の組に重複があるが、確率を考える上では問題ない

    def move(self, ship_type, direction) -> None:
        """
        敵のmoveを処理し、self.dfを更新
        direction = [1,0]などの移動分を表すベクトル
        self.df.loc[:, ship_type]を使うことでSettingWithCopyWarningをさけ、確実に元のdfを変更できるようにする
        """
        delta_x = direction[0]
        delta_y = direction[1]
        self.df.loc[:, ship_type] = self.df[ship_type].map(lambda x: (x[0] + delta_x , x[1] + delta_y))
        
        
        # 有効な座標以外の盤面を削除
        self.df = self.df[self.df[ship_type].map(lambda x: x in valid_coordinates())]

        # 座標がダブっている船を含む盤面を削除(移動によりダブってしまうことがある)
        self.remove_same_position()
    
    def attack(self, position) -> None:
        """
        敵のattackを処理し、self.dfを更新
        position = [1,0]などの相手の攻撃した座標
        """
        # positionの周囲1マスを取得(ここに相手がいることになる)
        # ここでは盤面の外の座標が入ってしまっても問題ない
        near_positions = [(position[0] + i, position[1] + j) for i in range(-1, 2) for j in range(-1, 2)]

        # self.dfの中から、near_positionsに含まれる座標を持つ行のみを残す
        # ただし、w,c,sが全て存在するとは限らないことに注意

        # self.dfの行が、near_positionsに含まれる座標を持つかどうかを判定する関数
        def is_valid(x): # xはself.dfの行
            for ship in self.ships:
                if x[ship] in near_positions:
                    return True
            # どの船もnear_positionsに含まれる座標を持っていない場合
            return False
            
        self.df = self.df[self.df.apply(is_valid, axis=1)]

    def hit(self, ship_type, position) -> None:
        """
        自分の攻撃がhitして、かつその船がまだ生きている時の処理
        """
        position = tuple(position) # 忘れずに
        self.df = self.df[self.df[ship_type] == position]
        # print(self.prob()) hit関数が動いているなら、ここを表示すると常に確率1の座標が存在するはず

    def miss(self, position) -> None:
        """
        自分の攻撃がmissした時の処理
        """
        # 結局、near/not_nearで処理するので何もしない
        pass

    def near(self, ship_type, position) -> None:
        """
        自分の攻撃の結果、ship_typeがnearにいた時の処理
        positionの周囲1マス(自身を含まない)にその船がいることが確定する
        """
        position = tuple(position)
        # near_positionsはpositionの周囲1マス(自身を含まない)の座標
        near_positions = [(position[0] + i, position[1] + j) for i in range(-1, 2) for j in range(-1, 2)]
        near_positions.remove(position) 
        self.df = self.df[self.df[ship_type].map(lambda x: x in near_positions)]

    def not_near(self, ship_type, position) -> None:
        """ 
        自分の攻撃の結果、ship_typeがnot_nearだった時の処理
        positionの周囲1マス(自身を含む)以外のマスにその船がいることが確定する
        """
        position = tuple(position)
        # near_positionsはpositionの周囲1マス(自身を含む)の座標
        near_positions = [(position[0] + i, position[1] + j) for i in range(-1, 2) for j in range(-1, 2)]
        self.df = self.df[self.df[ship_type].map(lambda x: x not in near_positions)]

    def prob(self):
        return self.df.stack().value_counts()/len(self.df)
    
    def where_to_attack(self):
        """
        self.dfの中から、確率高い座標を順に返す
        なお、enemy クラス内部の処理ではdictのkeyにできるという理由でtupleを使っていたが、ここでlistに戻す
        [[4, 2],[4, 0],...]
        """
        return [list(coordinate) for coordinate in self.prob().keys().tolist()]
    

class MyPlayer(Player):

    def __init__(self):

        # フィールドを2x2の配列として持っている．
        self.field = [[i, j] for i in range(Player.FIELD_SIZE)
                      for j in range(Player.FIELD_SIZE)]

        # 敵の盤面を管理するEnemyクラスのインスタンスを持たせる
        self.enemy = Enemy()

        # リストmake_not_near_coordinates()に存在する盤面の中からランダムに1つ選ぶ．
        positions = random.choice(make_not_near_coordinates())
        super().__init__(positions) # self.shipsが設定される

    #
    # 移動か攻撃かランダムに決める．
    # どれがどこへ移動するか，あるいはどこに攻撃するかもランダム．
    #
    def action(self) -> str: # json形式
        """
        行動の前にself.enemy.prob()、つまり相手の確率分布を更新
        """
        # 動いた方が確率が高くなるなら動くようにするとより良くなりそう
        
        # 可視化しやすいように、敵の盤面の確率を表示
        print(self.enemy.prob())

        to = None # UnboundLocalErrorを避けるためにNoneで初期化
        for coordinate in self.enemy.where_to_attack():
            if self.can_attack(coordinate):
                to = coordinate
                return json.dumps(self.attack(to)) # dict -> JSON形式の文字列

        # 相手が存在する可能性のあるマスに攻撃可能な座標がない場合は、この時点でまだreturnされていない

        # まずは、相手の船が存在する可能性があるマスに移動可能であれば移動
        # 本当は相手の船が存在する可能性があるマスの周囲でもOKだが、、
        for coordinate in self.enemy.where_to_attack(): # 敵の盤面の確率が高い座標から順に
            for ship in self.ships.values(): # shipオブジェクトについて回す
                if ship.can_reach(coordinate) and self.overlap(coordinate) is None:
                    to = coordinate
                    return json.dumps(self.move(ship.type, to)) # dict -> JSON形式の文字列
        
        # それでも無理なら、相手がいる可能性が最も高いマスにx座標を合わせる
        to = [None, None]
        to[0] = self.enemy.where_to_attack()[0][0]
        # to[1]は0からFIELD_SIZE-1までのランダム整数
        to[1] = random.randint(0, Player.FIELD_SIZE-1) # randintは両端を含む
        while not ship.can_reach(to) or not self.overlap(to) is None: # 移動できない　or 他のshipと重複している
                to[1] = random.randint(0, Player.FIELD_SIZE-1)
        return json.dumps(self.move(ship.type, to))

    def update(self, json_):
        """
        自分と相手それぞれの'condition'を更新する。
        自分のターンでも相手のターンでも実行する
        """
        super().update(json_) # 親クラスのupdateメソッドを呼び出す(自分の状態を更新)
        # 相手の船の存在状況を更新
        cond_e = json.loads(json_)['condition']['enemy'] # {"w":{"hp":1},"s":{"hp":1}}

        # 相手の船が存在するか否かを更新
        self.enemy.ships = list(cond_e.keys()) # like ["w", "c"]
        # 存在しない船についてはdataframeからカラムを削除
        self.enemy.df = self.enemy.df[self.enemy.ships]

    def enemy_update(self, json_):
        """
        相手のターンでは、相手の行動結果(result)を処理
        """
        result = json.loads(json_)['result']

        # {"moved":{"ship":"w","distance":[0,-2]}}を捉えて処理
        if "moved" in result:
            # 動いた船と方向を入れて、self.enemy.dfを更新する
            print(result)
            self.enemy.move(result["moved"]["ship"], result["moved"]["distance"])

        # {"attacked":{"position":[4,2],"hit":"s","near":["w"]}}を捉えて処理
        # このうち、"position"のみ使う(敵がどこを攻撃したかで敵の位置が絞れる)
        if "attacked" in result:
            # 攻撃された座標を取得し、self.enemy.dfを更新する
            attacked_position = result["attacked"]["position"]
            self.enemy.attack(attacked_position)

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
            # ヒットしていなかった時
            # 攻撃したマスに相手の船がないことが確定するが、この処理はnearで同時にできるのでここでは不要
            else:
                pass
            
            # nearによって、相手の船の位置が絞れる
            # それぞれの船について場所が絞れるから順番に処理
            for ship in self.enemy.ships: # self.enemy.ships is like ["w", "c"]
                if "hit" in result:
                    if ship == result["hit"]: # ヒットした船については処理済みなのでスキップ
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
        with sock.makefile(mode='rw', buffering=1) as sockfile:
            get_msg = sockfile.readline()
            print(get_msg)
            player = MyPlayer()
            sockfile.write(player.initial_condition()+'\n') # 自分で決めた初期状態を書き込む

            while True:
                info = sockfile.readline().rstrip() # sockfileから1行読み込む
                print(info)
                if info == "your turn":
                    # アクションをしてsockfileに書き込む
                    sockfile.write(player.action()+'\n')

                    # サーバからの応答を受け取る
                    get_msg = sockfile.readline()
                    # print(get_msg)
                    player.update(get_msg) # get_msgはJSON形式の文字列
                    # 自分のターンの時は、get_msgから自分の行動結果の情報を取得する
                    player.my_update(get_msg)

                elif info == "waiting":
                    # 相手ターンの時は、get_msgから相手の行動についての情報を取得する
                    get_msg = sockfile.readline()
                    # print(get_msg)
                    player.update(get_msg)
                    player.enemy_update(get_msg)

                    """
                    get_msgの中身
                    (自分のターンで"moved"を選択した場合、resultは返ってこない)
                    {
                    "result": {
                        "attacked": {
                        "position": [4, 2],
                        "hit":"s",
                        "near": []
                        }
                        or "moved": {
                        "ship":"w",
                        "distance":[-1,0]
                        }
                    },
                    "condition": {
                        "me": {
                        "w": {
                            "hp": 3,
                            "position": [4, 0]
                        },
                        "c": {
                            "hp": 2,
                            "position": [0, 4]
                        },
                        "s": {
                            "hp": 1,
                            "position": [4, 3]
                        }
                        },
                        "enemy": {
                        "w": {
                            "hp": 3
                        },
                        "c": {
                            "hp": 2
                        },
                        "s": {
                            "hp": 1
                        }
                        }
                    }
                    }
                    """
                elif info == "you win":
                    break
                elif info == "you lose":
                    break
                elif info == "even":
                    break
                else:
                    raise RuntimeError("unknown information")


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