import React, {useEffect, useState} from 'react';
import {Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis} from 'recharts';
import {api} from './api';

const pageSize = 100;
const hourLabel = hour => String(hour).padStart(2, '0') + ':00';
const delhiDate = () => new Intl.DateTimeFormat('sv-SE', {timeZone: 'Asia/Kolkata'}).format(new Date());

export default function DemandAnalytics() {
  const [offset, setOffset] = useState(0);
  const [coverage, setCoverage] = useState(null);
  const [route, setRoute] = useState('');
  const [date, setDate] = useState(delhiDate);
  const [profile, setProfile] = useState(null);

  useEffect(() => {
    const request = new AbortController();
    api.demandCoverage({limit: pageSize, offset}, request.signal).then(data => {
      if (!request.signal.aborted) setCoverage(data);
    }).catch(() => {
      if (!request.signal.aborted) setCoverage({status: 'error'});
    });
    return () => request.abort();
  }, [offset]);

  useEffect(() => {
    if (!route || !date) return;
    const request = new AbortController();
    api.demandProfile({route_id: route, date}, request.signal).then(data => {
      if (!request.signal.aborted) setProfile(data);
    }).catch(() => {
      if (!request.signal.aborted) setProfile({status: 'error'});
    });
    return () => request.abort();
  }, [route, date]);

  function changePage(next) {
    setCoverage(null);
    setProfile(null);
    setRoute('');
    setOffset(next);
  }

  const points = profile?.hours ?? [];
  const available = points.filter(point => Number.isFinite(point.estimated_ticketed_passengers));
  return <section className="analytics-section">
    <h2>Historical estimated ticket demand</h2>
    <p>Route-level estimates use the selected date’s weekday in Delhi. Bus capacity and segment occupancy are unavailable.</p>
    {!coverage && <p role="status">Loading historical coverage…</p>}
    {coverage?.status === 'error' && <p role="alert">Historical coverage could not be loaded.</p>}
    {coverage?.status === 'unavailable' && <p role="status">No validated historical data is loaded.</p>}
    {coverage?.status === 'available' && <>
      <p>{coverage.mapped_routes.toLocaleString('en-IN')} of {coverage.imported_routes.toLocaleString('en-IN')} GTFS routes are mapped.</p>
      <div className="demand-filters">
        <label>GTFS route <select value={route} onChange={event => {
          setProfile(null);
          setRoute(event.target.value);
        }}>
          <option value="">Choose a covered route</option>
          {coverage.routes.map(item => <option key={item.route_id} value={item.route_id}>{item.route}</option>)}
        </select></label>
        <label>Service date <input type="date" required value={date} onChange={event => {
          setProfile(null);
          setDate(event.target.value);
        }}/></label>
        {offset > 0 && <button className="text-btn" onClick={() => changePage(offset - pageSize)}>Previous routes</button>}
        {offset + pageSize < coverage.mapped_routes && <button className="text-btn" onClick={() => changePage(offset + pageSize)}>More routes</button>}
      </div>
      {route && date && !profile && <p role="status">Loading route demand…</p>}
      {profile?.status === 'error' && <p role="alert">Route demand could not be loaded.</p>}
      {points.length > 0 && <p role="status">{available.length} of {points.length} hourly estimates available.</p>}
      {available.length > 0 && <ResponsiveContainer width="100%" height={220}>
        <BarChart data={points} accessibilityLayer>
          <CartesianGrid vertical={false} stroke="#e4e5ed"/>
          <XAxis dataKey="hour" tickFormatter={hourLabel} minTickGap={24}/>
          <YAxis width={42}/>
          <Tooltip labelFormatter={hourLabel} formatter={value => [value, 'Estimated tickets']}/>
          <Bar dataKey="estimated_ticketed_passengers" fill="#6949d8"/>
        </BarChart>
      </ResponsiveContainer>}
      {points.length > 0 && <details>
        <summary>Hourly estimates table</summary>
        <table><thead><tr><th scope="col">Delhi time</th><th scope="col">Estimated tickets</th></tr></thead>
          <tbody>{points.map(point => <tr key={point.hour}><th scope="row">{hourLabel(point.hour)}</th>
            <td>{point.estimated_ticketed_passengers ?? 'Unavailable'}</td></tr>)}</tbody>
        </table>
      </details>}
    </>}
  </section>;
}
