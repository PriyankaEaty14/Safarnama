"""Audit a candidate bus run against GTFS stop order and timetable.

This does not establish that the tickets belong to one physical bus trip.
Run from ml/: python src/validate_candidate_run.py --run-id DL1PD8407_48
"""
import argparse
import json
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]


def seconds(value):
    try:
        h, m, s = map(int, str(value).split(':'))
        if m not in range(60) or s not in range(60) or h < 0:
            return None
        return h * 3600 + m * 60 + s
    except (ValueError, TypeError):
        return None


def positions(stops):
    d = {}
    for i, stop in enumerate(stops):
        d.setdefault(str(stop), []).append(i)
    return d


def possible_pairs(pos, start, end):
    return [(i, j) for i in pos.get(str(start), [])
            for j in pos.get(str(end), []) if i < j]


def evaluate_pattern(run, group):
    group = group.sort_values('stop_sequence').reset_index(drop=True)
    pos = positions(group['stop_id'].tolist())
    total = supported = ambiguous = 0
    assignments = []
    for ticket in run.itertuples(index=False):
        n = int(ticket.passenger_count)
        total += n
        pairs = possible_pairs(pos, ticket.start_stop_id, ticket.end_stop_id)
        if not pairs:
            continue
        supported += n
        if len(pairs) > 1:
            ambiguous += n
        assignments.append((ticket, pairs))
    # A ticket timestamp may represent issuance, not actual boarding.
    # Time proximity is a diagnostic only; no ticket-to-trip assertion is made.
    diffs = []
    for ticket, pairs in assignments:
        ticket_sec = (pd.Timestamp(ticket.created_at).hour * 3600
                      + pd.Timestamp(ticket.created_at).minute * 60
                      + pd.Timestamp(ticket.created_at).second)
        board_times = [seconds(group.iloc[i]['departure_time']) for i, _ in pairs]
        board_times = [x for x in board_times if x is not None]
        if board_times:
            diffs.append(min(abs(ticket_sec - t) for t in board_times) / 60)
    return {
        'trip_id': str(group.iloc[0]['trip_id']),
        'supported_passengers': supported,
        'excluded_passengers': total - supported,
        'ambiguous_passengers': ambiguous,
        'median_ticket_to_schedule_minutes': round(float(pd.Series(diffs).median()), 2) if diffs else None,
        'stop_count': len(group),
    }, group, assignments


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run-id', default='DL1PD8407_48')
    p.add_argument('--max-schedule-offset', type=float, default=30.0)
    args = p.parse_args()
    data = BASE / 'data' / 'processed'
    gtfs = BASE / 'data' / 'raw' / 'gtfs'
    out = BASE / 'outputs'
    out.mkdir(exist_ok=True)
    run = pd.read_parquet(data / 'candidate_bus_runs.parquet')
    run = run.loc[run['candidate_run_id'].eq(args.run_id)].copy()
    if run.empty:
        raise ValueError(f'Candidate run not found: {args.run_id}')
    if run['route'].nunique() != 1 or run['vehicle_number'].nunique() != 1:
        raise ValueError('Candidate run spans multiple routes or vehicles')
    run = run.sort_values('created_at')
    route = str(run.iloc[0]['route']).strip().upper()
    routes = pd.read_csv(gtfs / 'routes.txt', dtype=str, usecols=['route_id', 'route_short_name'])
    routes['route_short_name'] = routes['route_short_name'].str.strip().str.upper()
    ids = set(routes.loc[routes['route_short_name'].eq(route), 'route_id'])
    trips = pd.read_csv(gtfs / 'trips.txt', dtype=str, usecols=['route_id', 'trip_id'])
    trip_ids = set(trips.loc[trips['route_id'].isin(ids), 'trip_id'])
    if not trip_ids:
        raise ValueError(f'No GTFS trips found for {route}')
    times = pd.read_csv(gtfs / 'stop_times.txt', dtype=str,
                        usecols=['trip_id', 'stop_id', 'stop_sequence', 'departure_time'])
    times = times.loc[times['trip_id'].isin(trip_ids)].copy()
    times['stop_sequence'] = pd.to_numeric(times['stop_sequence'], errors='coerce')
    times = times.dropna(subset=['stop_sequence'])
    evaluations = [evaluate_pattern(run, g) for _, g in times.groupby('trip_id', sort=False)]
    if not evaluations:
        raise ValueError('No GTFS stop times for route')
    # Passenger support first; schedule proximity only breaks ties.
    evaluations.sort(key=lambda x: (-x[0]['supported_passengers'],
                      x[0]['median_ticket_to_schedule_minutes'] if x[0]['median_ticket_to_schedule_minutes'] is not None else float('inf'),
                      x[0]['trip_id']))
    best, group, assignments = evaluations[0]
    board = [0] * len(group)
    alight = [0] * len(group)
    excluded_ambiguous = 0
    for ticket, pairs in assignments:
        # Exclude ambiguous repeated-stop assignments instead of guessing.
        if len(pairs) != 1:
            excluded_ambiguous += int(ticket.passenger_count)
            continue
        i, j = pairs[0]
        board[i] += int(ticket.passenger_count)
        alight[j] += int(ticket.passenger_count)
    load = 0
    rows = []
    for i, stop in enumerate(group['stop_id'].astype(str)):
        load += board[i] - alight[i]
        if load < 0:
            raise AssertionError('Negative load: invalid accounting')
        rows.append({'stop_sequence_index': i, 'stop_id': stop,
                     'boardings': board[i], 'alightings': alight[i],
                     'ticket_observed_load': load})
    if load != 0 or sum(board) != sum(alight):
        raise AssertionError('Passenger conservation failed')
    profile = pd.DataFrame(rows)
    stops = pd.read_csv(gtfs / 'stops.txt', dtype=str, usecols=['stop_id', 'stop_name'])
    profile = profile.merge(stops.drop_duplicates('stop_id'), on='stop_id', how='left', validate='many_to_one')
    profile_path = out / 'audited_candidate_occupancy_profile.csv'
    profile.to_csv(profile_path, index=False)
    median = best['median_ticket_to_schedule_minutes']
    report = {
        'candidate_run_id': args.run_id,
        'route': route,
        'vehicle': str(run.iloc[0]['vehicle_number']),
        'ticket_records': len(run),
        'total_ticketed_passengers': int(run['passenger_count'].sum()),
        'gtfs_pattern_candidate': best['trip_id'],
        'pattern_supported_passengers': best['supported_passengers'],
        'excluded_repeated_stop_ambiguous_passengers': excluded_ambiguous,
        'profile_accounted_passengers': sum(board),
        'peak_ticket_observed_load': int(profile['ticket_observed_load'].max()),
        'median_ticket_to_schedule_minutes': median,
        'within_schedule_offset_threshold': bool(median is not None and median <= args.max_schedule_offset),
        'physical_trip_verified': False,
        'actual_bus_occupancy_verified': False,
        'notes': 'Ticket timestamps may be issuance times; GTFS service calendar, vehicle-trip identity and physical run continuity remain unverified.'
    }
    (out / 'audited_candidate_run_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    print('Saved:', profile_path)


if __name__ == '__main__':
    main()
