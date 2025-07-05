def extract_match_data(json_obj):
    matches = []
    for entry in json_obj.get("Value", []):
        match = {
            "event_id": entry.get("I"),
            "teams": {
                "team1": entry.get("O1"),
                "team2": entry.get("O2")
            },
            "odds": entry.get("E", []),
            "handicaps": entry.get("AE", []),
            "score": entry.get("SC", {})
        }
        matches.append(match)
    return matches
