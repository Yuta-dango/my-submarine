import random


# 2座標がnマス以内にあるかどうかを返す。
def near(pos1, pos2, n=1):
    return abs(pos1[0] - pos2[0]) <= n and abs(pos1[1] - pos2[1]) <= n


# 初期配置を決める。
def make_initial(field):
    while True:
        ps = random.sample(field, 3)
        # sは端に配置
        if ps[0][0] in [0, len(field) - 1] or ps[0][1] in [0, len(field) - 1]:
            continue
        # 艦同士が2マス以内に入らないようにする
        if near(ps[0], ps[1], 2) or near(ps[1], ps[2], 2) or near(ps[2], ps[0], 2):
            continue
        break
    return ps
