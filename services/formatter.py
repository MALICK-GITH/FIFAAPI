def format_odds(odds):
    formatted = []
    for o in odds:
        formatted.append({
            "type": o.get("T"),
            "group": o.get("G"),
            "value": o.get("C"),
            "handicap": o.get("P", None),
            "outcome": o.get("O")
        })
    return formatted
