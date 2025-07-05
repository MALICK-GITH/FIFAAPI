from services.formatter import format_odds
from services.predictor import predict_best_odds

class Match:
    def __init__(self, entry):
        self.event_id = entry.get("I")
        self.team1 = entry.get("O1")
        self.team2 = entry.get("O2")
        self.score = entry.get("SC", {})
        self.raw_odds = entry.get("E", [])
        self.handicaps = entry.get("AE", [])
        self.league = entry.get("L", "")
        self.sport_id = entry.get("SP", None)

        # Traitement des cotes
        self.odds = format_odds(self.raw_odds)
        self.best_bet = predict_best_odds(self.raw_odds)

    def get_teams(self):
        return f"{self.team1} vs {self.team2}"

    def get_score(self):
        sc = self.score.get("TS", {})
        return f"{sc.get('O1', 'N/A')} - {sc.get('O2', 'N/A')}"

    def summary(self):
        return {
            "event_id": self.event_id,
            "teams": self.get_teams(),
            "score": self.get_score(),
            "league": self.league,
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
            "odds": self.odds,
            "handicaps": self.handicaps,
            "best_bet": self.best_bet
        }
