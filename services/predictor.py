def predict_best_odds(odds_list):
    if not odds_list:
        return None
    sorted_odds = sorted(odds_list, key=lambda o: o.get("C", 0), reverse=True)
    return sorted_odds[0]  # meilleure cote
