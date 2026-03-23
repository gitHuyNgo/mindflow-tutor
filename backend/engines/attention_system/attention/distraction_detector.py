import time


class DistractionDetector:

    def __init__(self, away_threshold=2):

        self.away_start = None
        self.away_threshold = away_threshold
        self.triggered = False

    def update(self, distracted):

        now = time.time()

        if distracted:
            if self.away_start is None:
                self.away_start = now
                self.triggered = False

            away_time = now - self.away_start

            if away_time >= self.away_threshold and not self.triggered:
                self.triggered = True
                return True

        else:
            self.away_start = None
            self.triggered = False

        return False
