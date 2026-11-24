import React, {useEffect, useState} from 'react';
import {Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis} from 'recharts';
import {api} from './api';
import DemandAnalytics from './demand-analytics';

const metrics = [
  ['Agencies', 'agencies'], ['Stops', 'stops'], ['Routes', 'routes'],
  ['Trips', 'trips'], ['Stop-time records', 'stopTimes'],
];

const format = value => Number.isFinite(value) ? value.toLocaleString('en-IN') : 'Unavailable';
const serviceDay = new Intl.DateTimeFormat('en-IN', {dateStyle: 'medium', timeZone: 'UTC'});
const hourLabel = hour => `${String(hour % 24).padStart(2, '0')}:00${hour >= 24 ? ` (+${Math.floor(hour / 24)}d)` : ''}`;

export default function NetworkAnalytics() {
  const [data, setData] = useState(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const request = new AbortController();
    api.analytics(request.signal).then(summary => {
      if (!request.signal.aborted) {
        if (!summary?.counts) throw new Error('Missing schedule analytics');
        setData(summary);
      }
    }).catch(() => {
      if (!request.signal.aborted) setFailed(true);
    });
    return () => request.abort();
  }, [attempt]);

  if (failed) return <div className="message error" role="alert">
    Analytics could not be loaded. <button className="text-btn" onClick={() => {
      setFailed(false);
      setAttempt(value => value + 1);
    }}>Try again</button>
  </div>;
  if (!data) return <div className="message" role="status">Loading network analytics…</div>;

  const hours = (Array.isArray(data.scheduledDeparturesByHour) ? data.scheduledDeparturesByHour : [])
    .filter(({hour, trips}) => Number.isInteger(hour) && hour >= 0 && Number.isInteger(trips) && trips >= 0);
  const corridors = Array.isArray(data.corridors) ? data.corridors : [];
  return <section className="panel network-analytics" aria-label="Network statistics">
    <h2>Imported GTFS data</h2>
    <div className="metrics">{metrics.map(([label, key]) => <section className="panel metric" key={key}>
      <span>{label}</span><strong>{format(data.counts[key])}</strong>
    </section>)}</div>
    {data.serviceDates?.first && <p>Published calendar range · {data.serviceDates.first} to {data.serviceDates.last}</p>}
    <section className="analytics-section">
      <h2>Scheduled trip starts by hour</h2>
      <p>Each timetable trip is counted once at its first departure. Hours use Delhi time.</p>
      {hours.length ? <div className="hour-chart">
        <ResponsiveContainer width="100%" height={270}>
          <BarChart data={hours} margin={{top: 12, right: 8, bottom: 6, left: 0}} accessibilityLayer>
            <CartesianGrid vertical={false} stroke="#e4e5ed"/>
            <XAxis dataKey="hour" tickFormatter={hourLabel} minTickGap={24}/>
            <YAxis allowDecimals={false} width={42}/>
            <Tooltip labelFormatter={hourLabel} formatter={value => [format(value), 'Scheduled trips']}/>
            <Bar dataKey="trips" fill="#6949d8" radius={[4, 4, 0, 0]}/>
          </BarChart>
        </ResponsiveContainer>
      </div> : <div className="message" role="status">No scheduled trip departures are available.</div>}
    </section>
    <section className="analytics-section">
      <h2>Most scheduled stop-to-stop links</h2>
      <p>The ten directional links with the most traversals in the published timetable.</p>
      {corridors.length ? <div className="corridors-table"><table>
        <thead><tr><th scope="col">From</th><th scope="col">To</th><th scope="col">Traversals</th><th scope="col">Routes</th></tr></thead>
        <tbody>{corridors.map(link => <tr key={JSON.stringify([link.fromStopId, link.toStopId])}>
          <td>{link.fromStopName}</td><td>{link.toStopName}</td>
          <td>{format(link.scheduledTraversals)}</td><td>{format(link.distinctRoutes)}</td>
        </tr>)}</tbody>
      </table></div> : <div className="message" role="status">No scheduled corridors are available.</div>}
    </section>
    {data.scheduledServiceWeek?.length > 0 && <section className="analytics-section">
      <h2>Scheduled trips by service day</h2>
      <p>First seven calendar dates in the imported timetable, with service exceptions applied.</p>
      <ul className="service-week">{data.scheduledServiceWeek.map(day => <li key={day.serviceDate}>
        <span>{serviceDay.format(new Date(day.serviceDate))} · {day.weekend ? 'Weekend' : 'Weekday'}</span>
        <strong>{format(day.trips)} scheduled trips</strong>
      </li>)}</ul>
    </section>}
    <DemandAnalytics/>
  </section>;
}
