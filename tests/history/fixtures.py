"""Responses shaped like the Jolpica/Ergast JSON API."""


def race(round_no, name="British Grand Prix", season="1950", **extra):
    return {
        "season": season,
        "round": str(round_no),
        "raceName": name,
        "date": "1950-05-13",
        "Circuit": {
            "circuitId": "silverstone",
            "circuitName": "Silverstone Circuit",
            "Location": {"lat": "52.0786", "long": "-1.01694", "locality": "Silverstone", "country": "UK"},
        },
        **extra,
    }


def result(position, driver_id, given, family, constructor, points, grid, status="Finished", fastest_rank=None):
    res = {
        "number": str(position),
        "position": str(position),
        "positionText": str(position),
        "points": str(points),
        "Driver": {"driverId": driver_id, "givenName": given, "familyName": family, "nationality": "Italian"},
        "Constructor": {"constructorId": constructor.lower().replace(" ", "_"), "name": constructor},
        "grid": str(grid),
        "laps": "70",
        "status": status,
    }
    if status == "Finished":
        res["Time"] = {"millis": str(8003600 + position * 1000), "time": "2:13:23.6"}
    if fastest_rank:
        res["FastestLap"] = {"rank": str(fastest_rank), "lap": "2", "Time": {"time": "1:50.6"}}
    return res


def mrdata(total, offset, limit, **table):
    return {"MRData": {"limit": str(limit), "offset": str(offset), "total": str(total), **table}}
