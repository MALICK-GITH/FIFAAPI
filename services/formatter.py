def format_odds(odds):
    return [
        {
            "type": o.get("T"),
            "group": o.get("G"),
            "value": o.get("C"),
            "handicap": o.get("P", None)
        } for o in odds
    ]
