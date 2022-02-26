from time import time


class TimeCount:
    def __init__(self):
        self.started = time()
        self.point = self.started

    def __call__(self) -> float:
        p = time() - self.point
        self.point = time()
        return p

    def total(self) -> float:
        return time() - self.started


class IdGenerator:
    def __init__(self, start=0) -> None:
        self.num = start

    def __call__(self) -> int:
        self.num += 1
        return self.num


def nround(num: float, n: int = 3) -> float:
    try:
        _num1, _num2 = str(num).split('.')

        if len(_num2) > n:
            r = _num1 + '.' + _num2[0:n]
            return float(r)
        else:
            return float(num)
    except:
        return float(num)
