import React, {useEffect, useState} from 'react';
import {ExternalLink, Footprints, Map as MapIcon, MapPin} from 'lucide-react';
import {MapContainer, TileLayer, Marker, Polyline, Popup, Tooltip, useMap} from 'react-leaflet';
import {divIcon} from 'leaflet';
import 'leaflet/dist/leaflet.css';
import {api} from './api';
import {googleMapsLinks, stopCoordinates, shapeCoordinates} from './maps';
import {journeySegments} from './journey';
import {stopImage} from './stop-images';

function FitMap({points}){
  const map=useMap();
  const lastFit=React.useRef(null);
  useEffect(()=>{
    const observer=new ResizeObserver(()=>map.invalidateSize({pan:false}));
    observer.observe(map.getContainer());
    return ()=>observer.disconnect();
  },[map]);
  useEffect(()=>{
    const boundsKey=JSON.stringify(points);
    if(lastFit.current===boundsKey)return;
    lastFit.current=boundsKey;
    if(points.length>1)map.fitBounds(points,{padding:[36,36],maxZoom:14,animate:false});
    else if(points.length)map.setView(points[0],14,{animate:false});
  },[map,points]);
  return null;
}
function StopMapActions({stop}){
  const links=googleMapsLinks(stop);
  if(!links)return null;
  return <div className="stop-map-actions">
    <a href={links.search} target="_blank" rel="noopener noreferrer" aria-label={`Open ${stop.name} in Google Maps (opens in a new tab)`}><ExternalLink size={16}/> Open in Google Maps</a>
    <a href={links.directions} target="_blank" rel="noopener noreferrer" aria-label={`Walking directions from your location to ${stop.name} in Google Maps (opens in a new tab)`}><Footprints size={16}/> Walk from my location</a>
  </div>;
}

function StopMapPicker({stops,StopInput}){
  const [stopId,setStopId]=useState('');
  const selected=stops.find(stop=>stop.id===stopId);
  return <div className="stop-map-picker">
    <img className="stop-picker-photo" src="/images/delhi-stop.webp" alt="" width="140" height="74" loading="lazy" decoding="async"/>
    <div>
      <StopInput label="Find a bus stop" icon={MapPin} id="map-stop"
        stops={stops} value={stopId} onPick={setStopId}/>
    </div>
    {selected?<StopMapActions stop={selected}/>:<p>Choose a stop to get walking directions.</p>}
  </div>;
}

function StopMarker({stop,position,role,journey,serviceDate,now,StopCalls}){
  const icon=React.useMemo(()=>{
    const photo=document.createElement('img');
    photo.src=stopImage(stop.id,false);
    photo.alt='';
    photo.loading='lazy';
    const size=role?42:33;
    return divIcon({html:photo,className:`photo-marker marker-${role?.toLowerCase()||'stop'}`,iconSize:[size,size],iconAnchor:[size/2,size],popupAnchor:[0,-size],tooltipAnchor:[0,-size]});
  },[stop.id,role]);
  return <Marker position={position} icon={icon} title={stop.name} alt={stop.name} zIndexOffset={role?100:0}>
    <Tooltip>{role?role+' · ':''}{stop.name}</Tooltip>
    <Popup className="stop-map-popup" maxWidth={270}>
      <h3>{stop.name}</h3>{role&&<small>{role}</small>}
      {journey&&<StopCalls journey={journey} stopId={stop.id} stopName={()=>stop.name} serviceDate={serviceDate} now={now}/>}
      <StopMapActions stop={stop}/>
    </Popup>
  </Marker>;
}

export default function Explorer({stops,journey,query,selectedStretch,serviceDate,now,Header,Message,Badge,StopInput,StopCalls,StopItinerary}){
  const [geometry,setGeometry]=useState(null);
  const [mapState,setMapState]=useState('');
  const [tilesUnavailable,setTilesUnavailable]=useState(false);
  useEffect(()=>{
    if(!journey)return;
    const controller=new AbortController();
    setMapState('loading');
    setGeometry(null);
    api.routes(journey,controller.signal).then(data=>{if(!controller.signal.aborted){if(!Array.isArray(data?.legs))throw new Error('Invalid geometry response');setGeometry(data.legs);setMapState('');}}).catch(()=>{if(!controller.signal.aborted)setMapState('error');});
    return ()=>controller.abort();
  },[journey]);
  const colors=['#6d48ee','#0f9f85','#b87816'];
  const byId=new Map(stops.map(s=>[s.id,s]));
  const coords=id=>stopCoordinates(byId.get(id));
  const visibleIds=new Set(journey?journey.legs.flatMap(leg=>leg.stopIds):[query.origin,query.destination]);
  const mappedStops=stops.filter(stop=>visibleIds.has(stop.id)&&stopCoordinates(stop));
  const legs=(journey?.legs||[]).map((leg,i)=>({...leg,points:shapeCoordinates(geometry?.[i])}));
  const endpoints=journey?[journey.legs[0].stopIds[0],journey.legs.at(-1).stopIds.at(-1)]:[query.origin,query.destination];
  const transfers=new Set(legs.slice(1).flatMap((leg,i)=>[legs[i].stopIds.at(-1),leg.stopIds[0]]));
  const points=legs.flatMap(l=>l.points);
  const highlighted=selectedStretch?[coords(selectedStretch.from),coords(selectedStretch.to)].filter(Boolean):[];
  const fit=highlighted.length===2?highlighted:[...points,...mappedStops.map(stopCoordinates)];
  const stretchName=selectedStretch&&[selectedStretch.from,selectedStretch.to].map(id=>byId.get(id)?.name||id).join(' – ');
  return <><Header scene="route" section="ROUTE EXPLORER" title="Explore your route" description="See bus stops, journey segments, and transfer points across Delhi." Icon={MapIcon}/>
    <section className="panel map-panel"><div className="section-title"><div className="section-icon"><MapPin size={20}/></div><div><h2>{journey?'Selected journey':selectedStretch?'Selected stretch · Bus '+selectedStretch.route:'Delhi bus stops'}</h2><p>{journey?legs.map(l=>'Bus '+l.route).join(' · '):selectedStretch?'Crowding status on the selected stretch.':'Open a journey from the planner to see its route.'}</p></div></div>
    {mapState==='loading'&&<Message>Loading route geometry…</Message>}{mapState==='error'&&<Message error>Route geometry could not be loaded.</Message>}
    {geometry&&legs.some(leg=>leg.points.length<2)&&<Message>Verified shape geometry is unavailable for one or more legs. You can still inspect their stops.</Message>}
    {selectedStretch&&<div className="selected-stretch"><MapPin size={18}/><strong>{stretchName}</strong><Badge level={selectedStretch.level}/>{highlighted.length<2&&<span>Stop coordinates unavailable</span>}</div>}
    {stops.length>0&&<StopMapPicker stops={stops} StopInput={StopInput}/>}
    {tilesUnavailable&&<Message>Map background unavailable. Stops and verified route lines are still shown.</Message>}
    <MapContainer center={[28.635,77.25]} zoom={11} className="map" scrollWheelZoom={false} zoomAnimation={false}><TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" eventHandlers={{tileerror:()=>setTilesUnavailable(true)}}/><FitMap points={fit}/>
    {legs.map((leg,i)=>leg.points.length>1&&<Polyline key={i} positions={leg.points} pathOptions={{color:colors[i%colors.length],weight:6,opacity:.85}}><Tooltip>Bus {leg.route}</Tooltip></Polyline>)}
    {mappedStops.map(stop=>{
      const endpoint=endpoints.indexOf(stop.id);
      const isTransfer=transfers.has(stop.id);
      const role=endpoint===0?'Origin':endpoint===1?'Destination':isTransfer?'Transfer':null;
      return <StopMarker key={stop.id} stop={stop} position={coords(stop.id)} role={role} journey={journey} serviceDate={serviceDate} now={now} StopCalls={StopCalls}/>;
    })}
    </MapContainer><p className="map-note"><span>●</span> Origin <span>●</span> Destination <span>●</span> Transfer · Stop images are illustrative.</p>{journey&&<StopItinerary journey={journey} segments={journeySegments(journey)} stopName={id=>byId.get(id)?.name||id}/>}</section>
  </>;
}
