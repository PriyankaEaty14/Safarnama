import React, {useEffect, useState} from 'react';
import {api} from './api';
import {laterQuery} from './journey';

const weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const number = new Intl.NumberFormat('en-IN', {maximumFractionDigits: 1});

export function HistoricalDemand({legs, searchDate}) {
  const [results, setResults] = useState(null);
  useEffect(() => {
    const controller = new AbortController();
    const requests = new Map();
    setResults(null);
    const estimates = legs.map(leg => {
      const {date, time} = laterQuery({date:searchDate, time:'00:00'}, leg.start);
      const key = JSON.stringify([leg.routeId, date, time.slice(0,2)]);
      if (!requests.has(key)) {
        requests.set(key, api.historicalDemand({route_id:leg.routeId, date, time}, controller.signal)
          .catch(() => null));
      }
      return requests.get(key);
    });
    Promise.all(estimates).then(data => {
      if (!controller.signal.aborted) setResults(data);
    });
    return () => controller.abort();
  }, [legs, searchDate]);

  return <section className="stop-itinerary historical-demand" aria-label="Historical estimated ticket demand">
    <h3>Historical estimated ticket demand</h3>
    <p>Ticketed passengers per route-hour across scheduled trips. This figure does not measure live occupancy or seat availability.</p>
    {results === null ? <p role="status">Loading historical demand…</p> : <ul>
      {results.map((result, index) => <li key={index}>
        <strong>Bus {legs[index].route}</strong>
        {!result ? <span role="status">Historical demand could not be checked.</span>
          : result.status !== 'historical_estimate' || !Number.isFinite(result.estimated_ticketed_passengers)
            ? <span>{result.reason || 'Historical demand unavailable.'}</span>
            : <>
              <span>{weekdays[result.day_of_week]} · {String(result.hour).padStart(2,'0')}:00 IST</span>
              <span>{number.format(result.estimated_ticketed_passengers)} estimated ticketed passengers per route-hour</span>
              {result.historical_daily_std != null && <span>Historical standard deviation: {number.format(result.historical_daily_std)}</span>}
              {result.historical_calendar_days != null && <span>{result.historical_calendar_days} historical calendar days. These can include hours with zero recorded tickets.</span>}
              <small>Source: {result.source} · Model: {result.model}</small>
            </>}
      </li>)}
    </ul>}
  </section>;
}
