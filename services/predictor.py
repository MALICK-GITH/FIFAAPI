def predict_best_odds(odds_list):
    if not odds_list:
        return None
    sorted_odds = sorted(odds_list, key=lambda o: o.get("C", 0), reverse=True)
    best = sorted_odds[0]
    return {
        "type": best.get("T"),
        "group": best.get("G"),
        "value": best.get("C"),
        "handicap": best.get("P", None)
    }
