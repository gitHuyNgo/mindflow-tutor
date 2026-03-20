import time


class DistractionDetector:

    def __init__(self):

        self.away_start = None

        self.episode_history = []

        self.away_threshold = 4
        self.window_time = 60
        self.episode_trigger = 3

    def update(self, distracted):

        now = time.time()

        if distracted:

            if self.away_start is None:
                self.away_start = now

        else:

            if self.away_start:

                duration = now - self.away_start

                if duration > self.away_threshold:
                    self.episode_history.append(now)

                self.away_start = None

        self.cleanup(now)

        if len(self.episode_history) >= self.episode_trigger:

            self.episode_history.clear()
            return True

        return False

    def cleanup(self, now):

        self.episode_history = [
            t for t in self.episode_history
            if now - t < self.window_time
        ]
