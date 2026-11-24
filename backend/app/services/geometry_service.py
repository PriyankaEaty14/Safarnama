"""Align a trip's ordered stops to its ordered shape points."""

from sqlalchemy import text


MAX_STOP_SHAPE_DISTANCE_METRES = 300


def trip_geometry(db, route_id, trip_id, from_sequence, to_sequence):
    trip = db.execute(text("SELECT shape_id FROM trips WHERE id=:trip AND route_id=:route"), {"trip": trip_id, "route": route_id}).first()
    if not trip:
        return None
    shape_id = trip[0]
    if not shape_id:
        return {"status": "unavailable", "reason": "Trip has no shape", "coordinates": [], "shapeId": None}
    points = db.execute(text("SELECT lat,lng FROM shape_points WHERE shape_id=:id ORDER BY sequence"), {"id": shape_id}).all()
    stops = db.execute(text("SELECT st.stop_sequence,s.lat,s.lng FROM stop_times st JOIN stops s ON s.id=st.stop_id WHERE st.trip_id=:trip ORDER BY st.stop_sequence"), {"trip": trip_id}).all()
    if len(points) < 2 or len(stops) < 2:
        return {"status": "unavailable", "reason": "Insufficient shape or stop points", "coordinates": [], "shapeId": shape_id}
    sequences = [stop[0] for stop in stops]
    if from_sequence not in sequences or to_sequence not in sequences or from_sequence >= to_sequence:
        return {"status": "unavailable", "reason": "Requested stop sequence is not on this trip", "coordinates": [], "shapeId": shape_id}

    previous = [0.0] * len(points)
    backtrack = []
    distances = []
    for stop_index, (_, stop_lat, stop_lng) in enumerate(stops):
        best_cost = float("inf")
        best_index = 0
        current = []
        links = []
        stop_distances = []
        for point_index, (lat, lng) in enumerate(points):
            distance2 = ((lat-stop_lat)*111_000)**2 + ((lng-stop_lng)*97_000)**2
            stop_distances.append(distance2)
            if previous[point_index] < best_cost:
                best_cost, best_index = previous[point_index], point_index
            current.append(best_cost + distance2)
            links.append(best_index)
        previous = current
        backtrack.append(links)
        distances.append(stop_distances)
    point_index = min(range(len(points)), key=lambda i: previous[i])
    matched = [0] * len(stops)
    for stop_index in range(len(stops)-1, -1, -1):
        matched[stop_index] = point_index
        point_index = backtrack[stop_index][point_index]
    if any(distances[i][matched[i]] > MAX_STOP_SHAPE_DISTANCE_METRES**2 for i in range(len(stops))):
        return {"status": "unavailable", "reason": "Stop-to-shape alignment exceeds 300 m", "coordinates": [], "shapeId": shape_id}
    start = matched[sequences.index(from_sequence)]
    end = matched[sequences.index(to_sequence)]
    if end <= start:
        return {"status": "unavailable", "reason": "Shape segment is ambiguous", "coordinates": [], "shapeId": shape_id}
    return {"status": "available", "reason": None, "coordinates": [[lat, lng] for lat, lng in points[start:end+1]], "shapeId": shape_id}
