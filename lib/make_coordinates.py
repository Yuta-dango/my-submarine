import pandas as pd

def valid_coordinates() -> set: # 要素はtuple
    return {(x, y) for x in range(5) for y in range(5)}

def center_coordinates() -> set:
    return {(x, y) for x in range(1, 4) for y in range(1, 4)}

def make_all_coordinates():
    """
    return:
        すべての盤面のリスト
        (各盤面は、{"w": (x, y), "c": (x, y), "s": (x, y)} という形式のdict
    """
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

def all_nears(position, me=True) -> set:
    """
    args:
        position: list or tuple (座標)
        me: position自身を含めるかどうか
    return:
        positionに隣接する座標の集合(盤面にあるもののみ)
    """
    x, y = position
    # 内包表記めちゃ便利...
    ans = {(x + dx, y + dy) for dx in [-1, 0, 1] for dy in [-1, 0, 1] if 0 <= x + dx < 5 and 0 <= y + dy < 5}
    if not me:
        ans.remove(tuple(position))
    return ans

# 初期配置として、相手の攻撃時に同時にnearが出ないような配置を作成
def make_not_near_coordinates():
    ans = []
    for pattern in make_all_coordinates():
        data = {position: 0 for position in valid_coordinates()}
        for position in valid_coordinates():
            for ship in pattern:
                if is_near(pattern[ship], position):
                    data[position] += 1
        if max(data.values()) <= 1:
            ans.append(pattern)
    return ans

def is_near(position1, position2):
    return abs(position1[0] - position2[0]) <= 1 and abs(position1[1] - position2[1]) <= 1

def distance(position1, position2):
    return (position1[0] - position2[0])**2 + (position1[1] - position2[1])**2


def which_is_near_center(position1, position2):
    center = (2, 2)
    if (position1[0] - center[0])**2 + (position1[1] - center[1])**2 <= (position2[0] - center[0])**2 + (position2[1] - center[1])**2:
        return position1
    else:
        return position2

def choose_nearest(position, candidates):
    """
    args:
        position: tuple (座標) この座標に近い座標を選ぶ
        candidates: list of tuple (座標)
    """
    # min関数にはkey引数があるので、これを使うと便利
    return min(candidates, key=lambda x: distance(position, x))


def make_near_x_or_y(position, target):
    """
    args:
        position: tuple(自分の座標)targetに近づけたい
        target: tuple (座標)
    return:
        x座標かy座標をtargetに近づけた座標(移動距離が短い方)
    """
    x, y = position
    tx, ty = target
    if abs(x - tx) <= abs(y - ty):
        return (tx, y)
    else:
        return (x, ty)


# tests
def test_all_nears():
    assert all_nears([0, 0], me=False) == {(0, 1), (1, 0), (1, 1)}
    assert all_nears([0, 0]) == {(0, 0), (0, 1), (1, 0), (1, 1)}
    assert all_nears([2, 3], me=False) == {(1, 2), (1, 3), (1, 4), (2, 2), (2, 4), (3, 2), (3, 3), (3, 4)}

def test_which_is_near_center():
    assert which_is_near_center((0, 0), (2, 2)) == (2, 2)
    assert which_is_near_center((0, 0), (0, 1)) == (0, 1)
    assert which_is_near_center((1, 1), (0, 2)) == (1, 1)
    
def test_make_near_x_or_y():
    assert make_near_x_or_y((0, 0), (2, 2)) == (2, 0)
    assert make_near_x_or_y((0, 0), (3, 4)) == (3, 0)
    assert make_near_x_or_y((1, 2), (2, 4)) == (2, 2)

if __name__ == '__main__':
    import doctest
    import pytest # pytest lib/make_coordinates.py を実行すると、テストが実行される
    doctest.testmod()