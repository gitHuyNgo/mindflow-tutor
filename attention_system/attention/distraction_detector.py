import time


class DistractionDetector:

    def __init__(self, away_threshold=4):

        self.away_start = None

        self.episode_history = []

        self.away_threshold = away_threshold
        self.long_threshold = self.away_threshold * 4

        self.window_time = 60
        self.episode_trigger = 3

        self.triggered = False
        self.long_triggered = False

    def update(self, distracted):

        now = time.time()

        if distracted:

            if self.away_start is None:
                self.away_start = now
                self.triggered = False
                self.long_triggered = False

            away_time = now - self.away_start

            # RULE 1: nhìn đi quá lâu (4 * threshold)
            if away_time > self.long_threshold and not self.long_triggered:

                self.long_triggered = True

                return True

            # RULE 2: nhìn đi > threshold → count episode
            if away_time > self.away_threshold and not self.triggered:

                self.episode_history.append(now)

                self.triggered = True

                self.cleanup(now)

                if len(self.episode_history) >= self.episode_trigger:

                    self.episode_history.clear()

                    return True

        else:

            self.away_start = None
            self.triggered = False
            self.long_triggered = False

        return False

    def cleanup(self, now):

        self.episode_history = [
            t for t in self.episode_history
            if now - t < self.window_time
        ]
