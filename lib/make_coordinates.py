import pandas as pd

def valid_coordinates():
    return {(x, y) for x in range(5) for y in range(5)}

def make_all_coordinates():
    coordinates = valid_coordinates()
    all_coordinates = []
    for coordinate_w in coordinates:
        w = coordinate_w
        for coordinate_c in coordinates:
            if coordinate_c == w:
                continue
            c = coordinate_c
            for coordinate_s in coordinates:
                if coordinate_s == w or coordinate_s == c:
                    continue
                s = coordinate_s
                all_coordinates.append({"w": w, "c": c, "s": s})
    return all_coordinates

def near(position1, position2):
    return abs(position1[0] - position2[0]) <= 1 and abs(position1[1] - position2[1]) <= 1

# 初期配置として、相手の攻撃時に同時にnearが出ないような配置を作成
def make_not_near_coordinates():
    ans = []
    for pattern in make_all_coordinates():
        data = {position: 0 for position in valid_coordinates()}
        for position in valid_coordinates():
            for ship in pattern:
                if near(pattern[ship], position):
                    data[position] += 1
        if max(data.values()) <= 1:
            ans.append(pattern)
    return ans
