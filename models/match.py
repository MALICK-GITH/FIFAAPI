from services.formatter import format_odds
from services.predictor import predict_best_odds

class Match:
    def __init__(self, entry):
        self.event_id = entry.get("I")
        self.team1 = entry.get("O1")
        self.team2 = entry.get("O2")
        self.score_raw = entry.get("SC", {})
        self.odds_raw = entry.get("E", [])
        self.handicaps = entry.get("AE", [])
        self.league = entry.get("L", "")
        self.sport_id = entry.get("SP", None)
        self.country = entry.get("CO", "")
        self.status = entry.get("C", 0)

        # Traitements enrichis
        self.odds = format_odds(self.odds_raw)
        self.best_bet = predict_best_odds(self.odds_raw)
        self.score = self._parse_score(self.score_raw)

    def _parse_score(self, score_data):
        try:
            ts = score_data.get("TS", {})
            return {
                "team1": ts.get("O1", "0"),
                "team2": ts.get("O2", "0")
            }
        except Exception:
            return {"team1": "N/A", "team2": "N/A"}

    def get_teams(self):
        return f"{self.team1} vs {self.team2}"

    def is_live(self):
        return self.status == 1

    def summary(self):
        return {
            "event_id": self.event_id,
            "teams": self.get_teams(),
            "score": self.score,
            "league": self.league,
            "country": self.country,
            "is_live": self.is_live(),
            "best_bet": self.best_bet,
            "odds": self.odds
        }

    def to_dict(self):
        return {
            "event_id": self.event_id,
            "team1": self.team1,
            "team2": self.team2,
            "score": self.score,
            "league": self.league,
            "sport_id": self.sport_id,
            "country": self.country,
            "handicaps": self.handicaps,
            "odds": self.odds,
            "best_bet": self.best_bet,
            "status": self.status
        }
