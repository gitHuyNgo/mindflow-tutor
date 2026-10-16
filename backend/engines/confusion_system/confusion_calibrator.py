import time
from typing import Dict, Optional, Tuple, Any

# Calibrated weights reflecting cognitive confusion correlation
# Positive: indicates potential confusion/disequilibrium
# Negative: strongly inhibits confusion (e.g. happiness, active satisfaction)
DEFAULT_EMOTION_CONFUSION_WEIGHTS: Dict[str, float] = {
    "surprise": 0.60,   # cognitive surprise / disequilibrium
    "anger": 0.55,      # frustration / furrowed brow
    "fear": 0.45,       # helplessness or anxiety
    "sadness": 0.40,    # discouragement
    "disgust": 0.35,    # mild aversion / confusion
    "contempt": 0.30,   # skepticism
    "neutral": 0.05,    # baseline focus
    "happiness": -0.60, # strong inhibitor: learner understands
}

# Thresholds for sensitivity profiles
SENSITIVITY_PROFILES = {
    "low": {
        # Strict: Minimizes false positives to prevent interrupting flow state
        "trigger_threshold": 0.55,
        "clear_threshold": 0.20,
        "smoothing_alpha": 0.20,
        "min_sustained_seconds": 3.5,
    },
    "medium": {
        # Balanced: Standard tutoring behavior
        "trigger_threshold": 0.45,
        "clear_threshold": 0.20,
        "smoothing_alpha": 0.30,
        "min_sustained_seconds": 2.5,
    },
    "high": {
        # Sensitive: Eager proactive intervention
        "trigger_threshold": 0.30,
        "clear_threshold": 0.15,
        "smoothing_alpha": 0.40,
        "min_sustained_seconds": 1.5,
    },
}


class ConfusionCalibrator:
    """
    Calibrates raw facial emotion signals to infer student confusion with
    temporal exponential moving average (EMA) smoothing and hysteresis.
    Dramatically reduces false positive rate (FPR) during deep focus/squinting.
    """

    def __init__(
        self,
        sensitivity: str = "medium",
        custom_weights: Optional[Dict[str, float]] = None,
    ):
        self.weights = custom_weights or DEFAULT_EMOTION_CONFUSION_WEIGHTS
        self.sensitivity = sensitivity if sensitivity in SENSITIVITY_PROFILES else "medium"
        self.config = SENSITIVITY_PROFILES[self.sensitivity]

    def set_sensitivity(self, level: str):
        if level in SENSITIVITY_PROFILES:
            self.sensitivity = level
            self.config = SENSITIVITY_PROFILES[level]

    def compute_instantaneous_score(
        self,
        top_emotion: Optional[str],
        emotion_scores: Optional[Dict[str, float]] = None,
    ) -> float:
        """Compute frame-level raw confusion score in [0.0, 1.0]."""
        if not top_emotion and not emotion_scores:
            return 0.0

        if emotion_scores:
            # Weighted sum over full distribution
            score = 0.0
            for em, prob in emotion_scores.items():
                w = self.weights.get(em.lower(), 0.0)
                score += w * prob
            # Clamp to [0.0, 1.0]
            return max(0.0, min(1.0, score))

        # Fallback to top-1 emotion lookup
        w = self.weights.get(top_emotion.lower(), 0.0) if top_emotion else 0.0
        return max(0.0, min(1.0, w))

    def update(
        self,
        current_smoothed: float,
        is_currently_confused: bool,
        top_emotion: Optional[str],
        emotion_scores: Optional[Dict[str, float]] = None,
        confused_since: Optional[float] = None,
        now: Optional[float] = None,
    ) -> Tuple[bool, float, Optional[float], Dict[str, Any]]:
        """
        Update the calibrated confusion state with hysteresis.
        Returns: (is_confused, new_smoothed_score, new_confused_since, details)
        """
        now = now or time.time()
        instant_score = self.compute_instantaneous_score(top_emotion, emotion_scores)

        # Exponential moving average smoothing
        alpha = self.config["smoothing_alpha"]
        new_smoothed = (alpha * instant_score) + ((1.0 - alpha) * current_smoothed)

        trigger_thresh = self.config["trigger_threshold"]
        clear_thresh = self.config["clear_threshold"]
        min_seconds = self.config["min_sustained_seconds"]

        new_is_confused = is_currently_confused
        new_confused_since = confused_since

        if new_smoothed >= trigger_thresh:
            if new_confused_since is None:
                new_confused_since = now
            elapsed = now - new_confused_since
            if elapsed >= min_seconds:
                new_is_confused = True
        elif new_smoothed <= clear_thresh:
            new_is_confused = False
            new_confused_since = None
        else:
            # Hysteresis band: retain previous confusion state, pause or decay timer
            if not is_currently_confused and new_confused_since is not None:
                # Did not reach threshold long enough
                new_confused_since = None

        details = {
            "instant_score": round(instant_score, 4),
            "smoothed_score": round(new_smoothed, 4),
            "sensitivity": self.sensitivity,
            "trigger_threshold": trigger_thresh,
            "is_confused": new_is_confused,
        }

        return new_is_confused, new_smoothed, new_confused_since, details
