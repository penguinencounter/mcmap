from datetime import datetime
import time


class ETA:
    def __init__(self, rolling_average_count: int = 10):
        self.rolling_avg_count = rolling_average_count
        self.considered = []
        self.hist = []

    def step(self):
        if len(self.hist) > 0:
            self.considered.append(time.time() - self.hist[-1])
        self.hist.append(time.time())
        if len(self.considered) > self.rolling_avg_count:
            self.considered.pop(0)
            self.hist.pop(0)

    def get(self, remaining: float) -> str:
        if len(self.considered) < self.rolling_avg_count:
            return f'? ({len(self.considered)}/{self.rolling_avg_count})'
        avg_time_per_step = sum(self.considered) / len(self.considered)
        eta = avg_time_per_step * remaining
        return datetime.strftime(datetime.utcfromtimestamp(eta), '%H:%M:%S')
