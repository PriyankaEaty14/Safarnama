import React, {useEffect,useState,lazy,Suspense} from 'react';
import {createRoot} from 'react-dom/client';
import {HashRouter,NavLink,Route,Routes,useNavigate,useLocation} from 'react-router-dom';
import {BusFront,Route as RouteIcon,Map as MapIcon,ChartNoAxesCombined,ArrowDownUp,Search,Clock3,UsersRound,ChevronDown,MapPin,CalendarDays,Navigation,SlidersHorizontal,Menu, X, Layers3, CircleHelp, ArrowRight} from 'lucide-react';
import './styles.css';
import {api} from './api';
import {HistoricalDemand} from './historical-demand';
import {stopImage} from './stop-images';
import {compareJourneys,journeySegments,laterQuery,journeyFare,scheduledStops,transferBetween,callsAtStop,delhiDateTime,distinctJourneys} from './journey';

const labels={seats:'Seats available',standing:'Standing room',crowded:'Crowded'};
const preferences=[['fastest','Fastest',Clock3],['balanced','Balanced',SlidersHorizontal]];
const nav=[['/','Journey planner',RouteIcon],['/map','Route explorer',MapIcon],['/analytics','Network analytics',ChartNoAxesCombined]];
const initial={origin:'',destination:'',date:'',time:'',preference:'fastest'};
const time=value=>Number.isFinite(value)?String(((Math.floor(value/60)%24)+24)%24).padStart(2,'0')+':'+String(((value%60)+60)%60).padStart(2,'0')+(Math.floor(value/1440)!==0?' ('+(value>=0?'+':'')+Math.floor(value/1440)+'d)':''):'—';
const NetworkAnalytics = lazy(() => import('./analytics'));
const Explorer = lazy(() => import('./explorer'));
function Badge({level}){return <span className={'badge '+(level||'unknown')}><i/>{labels[level]||'Prediction unavailable'}</span>;}
function Message({children,error=false}){return <div className={'message '+(error?'error':'')} role={error?'alert':'status'}>{children}</div>;}
function Wordmark({className}){
  return <span className={`wordmark ${className}`}><span>SAFAR</span><span>NAMA</span></span>;
}

function Sidebar({open,close}) {
  return <aside className={'sidebar '+(open?'open':'')}>
    <div className="brand"><span><BusFront size={23}/></span><div><Wordmark className="sidebar-wordmark"/><small>DELHI BUS NETWORK</small></div><button className="mobile-close" aria-label="Close menu" onClick={close}><X/></button></div>
    <nav aria-label="Main navigation">{nav.map(([to,label,Icon])=><NavLink end={to==='/'} key={to} to={to} onClick={close}><Icon size={19}/>{label}</NavLink>)}</nav>
    <div className="sidebar-bottom"><div className="side-info"><Layers3 size={18}/><div><strong>Delhi bus network</strong><small>Bus journeys · IST</small></div></div><div className="side-footer"><CircleHelp size={16}/> Safarnama · Phase 1</div></div>
  </aside>;
}
function Header({section,title,description,Icon,scene}){
  return <header className={`hero hero-${scene}`}>
    <img className="hero-photo" src={`/images/delhi-${scene}.webp`} alt="" aria-hidden="true" fetchPriority="high"/>
    <div className="hero-copy">
      <div className="eyebrow"><Icon size={17}/>{section}</div>
      <h1>{title}</h1>
      <p>{description}</p>
    </div>
  </header>;
}
function StopInput({label,icon:Icon,id,stops,value,onPick}){
  const selected=stops.find(stop=>stop.id===value);
  const [draft,setDraft]=useState('');
  const [focused,setFocused]=useState(false);
  const [search,setSearch]=useState(null);
  const term=selected ? '' : draft.trim();
  const matches=search?.term===term ? search.items : [];
  function pick(stop){
    onPick(stop.id);
    setDraft('');
    setFocused(false);
  }
  useEffect(()=>{
    if(!focused||!term)return;
    const controller=new AbortController();
    const timer=setTimeout(async ()=>{
      try{
        const items=await api.searchStops(term,controller.signal);
        if(!Array.isArray(items))throw new Error('Invalid stop response');
        if(!controller.signal.aborted)setSearch({term,items});
      }catch{
        if(!controller.signal.aborted)setSearch({term,items:[],error:true});
      }
    },180);
    return ()=>{clearTimeout(timer);controller.abort();};
  },[focused,term]);
  return <div className="stop-field" onBlur={event=>{
      if(!event.currentTarget.contains(event.relatedTarget))setFocused(false);
    }}>
    <label htmlFor={id}>{label}</label><div className="input-wrap"><Icon size={18}/>
      <input id={id} value={selected?.name??draft} placeholder="Search bus stops" autoComplete="off"
        onFocus={()=>setFocused(true)}
        onChange={event=>{setDraft(event.target.value);if(value)onPick('');setFocused(true);}}
        onKeyDown={event=>{
          if(event.key==='Escape')setFocused(false);
          if(event.key==='Enter'&&focused&&matches.length){event.preventDefault();pick(matches[0]);}
          if(event.key==='ArrowDown'&&focused&&matches.length){
            event.preventDefault();
            event.currentTarget.closest('.stop-field').querySelector('.suggestions button')?.focus();
          }
        }}/>
    </div>
    {focused&&term&&<div className="suggestions" aria-label={label+' stop suggestions'}>
      {search?.term!==term?<span role="status">Searching stops…</span>:search.error?<span role="status">Stop search unavailable</span>:matches.length?
        matches.map(stop=><button type="button" key={stop.id} onMouseDown={event=>event.preventDefault()} onClick={()=>pick(stop)}>
          {stop.name}<small> · {stop.code||stop.id}</small>
        </button>):<span role="status">No matching stops</span>}
    </div>}
  </div>;
}
function ArrivalDelta({minutes}){
  return <span className="arrival-delta">{minutes===0?'Earliest arrival':minutes>0?`Arrive ${minutes} min later`:`Arrive ${-minutes} min earlier`}</span>;
}

function Comparison({journeys}){
  const {earliest}=compareJourneys(journeys);
  if(!earliest)return null;
  return <section className="comparison" aria-label="Journey comparison">
    <div className="results-header"><div><h2>Compare journey options</h2><p>Arrival times include the wait before boarding.</p></div></div>
    <div className="comparison-grid"><article className="panel compare-card">
      <h3><Clock3 size={18}/>Fastest arrival</h3>
      <div className="compare-times"><strong>{time(earliest.arrival)}</strong><ArrivalDelta minutes={0}/></div>
      <p>{earliest.legs.map(leg=>'Bus '+leg.route).join(' → ')} · Departs {time(earliest.departure)} · {earliest.legs.length===1?'Direct':`${earliest.legs.length-1} transfer${earliest.legs.length===2?'':'s'}`}</p>
      <FareLabel fare={journeyFare(earliest)} total/>
    </article><article className="panel compare-card">
      <h3><UsersRound size={18}/>Crowding comparison unavailable</h3>
      <p>No validated trip segment crowding estimates are available, so journey comfort cannot be compared.</p>
    </article></div>
  </section>;
}

function DepartureOptions({baseline,query,active,setActive,windows,setWindows}){
  const [pending,setPending]=useState(false);
  const request=React.useRef(null);
  useEffect(()=>()=>request.current?.abort(),[]);
  async function load(){
    request.current?.abort();
    const controller=new AbortController();
    request.current=controller;
    setPending(true);
    const entries=await Promise.all([15,30].map(async offset=>{
      const shifted=laterQuery(query,offset);
      try{
        const items=await api.journeys(shifted,controller.signal);
        return [offset,{items:distinctJourneys(items),query:shifted}];
      }catch{return [offset,{error:true,query:shifted}];}
    }));
    if(!controller.signal.aborted){
      const updated=Object.fromEntries(entries);
      setWindows(updated);
      setActive(current=>updated[current]?.error?0:current);
      setPending(false);
    }
  }
  const reference=compareJourneys(baseline).earliest;
  return <section className="panel departure-panel" aria-labelledby="leave-later">
    <div className="results-header"><div><h2 id="leave-later">Could leaving later help?</h2><p>Compare the earliest bus in each departure window.</p></div>
      <button className="text-btn" disabled={pending} onClick={load}><Clock3 size={17}/>{pending?'Checking…':windows?'Recheck times':'Check later departures'}</button>
    </div>
    {pending&&<Message>Checking departures 15 and 30 minutes later…</Message>}
    {windows&&<div className="departure-grid">{[0,15,30].map(offset=>{
      const window=offset?windows[offset]:{items:baseline,query};
      const {earliest}=compareJourneys(window?.items||[]);
      const dayChange=window.query.date!==query.date;
      const delta=earliest&&reference?earliest.arrival+1440*Number(dayChange)-reference.arrival:null;
      return <button className="departure-option" type="button" disabled={window.error} aria-pressed={active===offset} key={offset} onClick={()=>setActive(offset)}>
        <strong>{window.query.time} IST {dayChange&&'(next day)'}</strong><small>{offset?`+${offset} minutes`:'Original search'}</small>
        {window.error?<span>Couldn’t load this time</span>:earliest?<><span>Arrives {time(earliest.arrival)}</span>{offset>0&&delta!==null&&<ArrivalDelta minutes={delta}/>}</>:<span>No journeys found</span>}
      </button>;
    })}</div>}
  </section>;
}

function CrowdingStrip({segments,stopName,onSelect}){
  const available = segments.filter(segment => labels[segment.level]);
  if(!available.length)return null;
  return <div className="crowding-strip-wrap"><span>Crowding status by stretch</span><div className="crowding-strip" role="group" aria-label="Select a stretch to show it on the map">{available.map(segment=>{
    const title=`Bus ${segment.route}, ${stopName(segment.from)} to ${stopName(segment.to)} · ${labels[segment.level]||'Prediction unavailable'}`;
    return <button key={segment.legIndex+'-'+segment.index} className={labels[segment.level]?segment.level:'unknown'} type="button" aria-label={title+' · View on map'} title={title} onClick={()=>onSelect(segment)}/>;
  })}</div></div>;
}

function PredictionEvidence({prediction,loading,error}){
  if(loading)return <p className="prediction-evidence" role="status">Checking crowding availability…</p>;
  if(error)return <p className="prediction-evidence" role="status">Crowding availability could not be checked.</p>;
  const available=['available','historical_estimate','partially_available'].includes(prediction?.status);
  if(!available)return <p className="prediction-evidence">Crowding information is unavailable because validated segment-level passenger-load data is unavailable.</p>;
  return <div className="prediction-evidence">
    <strong>{prediction.status==='partially_available'?'Some segments have an estimate':'Crowding estimate available'}</strong>
    <div>{prediction.source&&<span>{prediction.source}</span>}
      {Number.isFinite(prediction.confidence)&&<span>Confidence · {Math.round(prediction.confidence*100)}%</span>}</div>
  </div>;
}

const formatFare = new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:2,minimumFractionDigits:0});
function FareLabel({fare,total=false}){
  return <span className={`fare-label ${fare==null?'fare-unknown':total?'fare-total':'fare-leg'}`}>
    {fare==null?'Fare unavailable':<><strong>{formatFare.format(fare)}</strong><span>{total?'total fare':'bus fare'}</span></>}
  </span>;
}

function StopThumb({id,className=''}) {
  return <img className={`stop-thumb ${className}`} src={stopImage(id,false)} alt="" loading="lazy" decoding="async"/>;
}

function StopPreview({journey,stopName,onSelect}){
  const ids=[...new Set(journey.legs.flatMap(leg=>leg.stopIds))];
  const preview=ids.length>3?[ids[0],ids[Math.floor(ids.length/2)],ids.at(-1)]:ids;
  return <div className="journey-stop-preview" aria-label="Stops on this journey">{preview.map(id=>
    <button type="button" key={id} onClick={()=>onSelect(id)} aria-label={`Check bus timing at ${stopName(id)}`}>
      <StopThumb id={id}/><span>{stopName(id)}</span>
    </button>)}</div>;
}

function StopCalls({journey,stopId,stopName,serviceDate,now}){
  const calls=callsAtStop(journey,stopId,serviceDate,now);
  const states={upcoming:'Scheduled to reach',due:'Due at stop',departed:'Scheduled to have left','arrival-passed':'Scheduled arrival passed',unknown:'Scheduled time unavailable'};
  return <div className="stop-calls"><strong>{stopName(stopId)}</strong>
    {calls.length?calls.map(call=>{
      const callTime=call.state==='departed'?call.departure:call.arrival??call.departure;
      const wording=call.state==='upcoming'&&call.arrival==null?'Scheduled to depart':states[call.state];
      return <span className={`call-status call-${call.state}`} key={call.legIndex+'-'+call.index}>
        Bus {call.route} · {wording}{call.state!=='unknown'&&` · ${time(callTime)} IST`}
      </span>;
    }):<span>This journey does not serve this stop.</span>}
  </div>;
}

function TransferNote({previous,next,stopName,minimumSeconds}){
  const transfer=transferBetween(previous,next);
  const sameStop=transfer.from===transfer.to;
  return <div className="transfer-note">
    <strong>{sameStop?`Change buses at ${stopName(transfer.from)}`:`Change stops from ${stopName(transfer.from)} to ${stopName(transfer.to)}`}</strong>
    <span>Get off bus {previous.route} at {time(transfer.arrival)} · Board bus {next.route} at {time(transfer.departure)}</span>
    <span>{transfer.minutes===null?'Scheduled transfer time unavailable':`${transfer.minutes} min ${sameStop?'scheduled wait':'between buses, including time to reach the next stop'}`}</span>
    {!sameStop&&Number.isFinite(minimumSeconds)&&<span>GTFS minimum connection time · {Math.ceil(minimumSeconds / 60)} min</span>}
  </div>;
}

function StopItinerary({journey,segments,stopName}){
  return <section className="stop-itinerary" aria-label="Stops, transfers and fares">
    <div className="itinerary-heading"><div><h3>Stop-by-stop itinerary</h3><p>Scheduled times in IST</p></div><FareLabel fare={journeyFare(journey)} total/></div>
    {journey.legs.map((leg,i)=><React.Fragment key={i}>
      {i>0&&<TransferNote previous={journey.legs[i-1]} next={leg} stopName={stopName} minimumSeconds={journey.transferMinimumSeconds}/>}
      <div className="itinerary-leg">
        <div className="itinerary-leg-heading"><strong><BusFront size={17}/> Bus {leg.route}</strong><FareLabel fare={leg.fareInr>=0&&Number.isFinite(leg.fareInr)?leg.fareInr:null}/></div>
        <ol>{scheduledStops(leg).map(({id,first,last,arrival,departure},index)=>{
          const segment=segments.find(item=>item.legIndex===i&&item.index===index);
          const hasArrival=Number.isFinite(arrival);
          const hasDeparture=Number.isFinite(departure);
          const times=first&&!last&&hasDeparture?`Depart ${time(departure)}`:last&&hasArrival?`Arrive ${time(arrival)}`:hasArrival&&hasDeparture&&arrival!==departure?`Arrive ${time(arrival)} · Depart ${time(departure)}`:hasArrival||hasDeparture?time(arrival??departure):'Time unavailable';
          const evidence=[segment?.sampleSize!=null?`${segment.sampleSize} comparable trips`:null,segment?.timeWindow].filter(Boolean);
          return <li key={index}>
            <div className="itinerary-stop"><StopThumb id={id}/><div><strong>{stopName(id)}</strong>{(first||last)&&<span>{first?'Board here':'Get off here'}</span>}</div></div>
            <span className="itinerary-time">{times}</span>
            {labels[segment?.level]&&<div className="itinerary-crowd"><Badge level={segment.level}/>{evidence.length>0&&<small>{evidence.join(' · ')}</small>}</div>}
          </li>;
        })}</ol>
      </div>
    </React.Fragment>)}
  </section>;
}

function JourneyCard({journey,recommended,stopName,onMap,query,earliestArrival,watchedStop,setWatchedStop,now}){
  const [expanded,setExpanded]=useState(false);
  const {legs,busiest}=journey;
  const transfers=Math.max(0,legs.length-1);
  const firstStop = stopName(legs[0].stopIds[0]);
  const lastStop = stopName(legs.at(-1).stopIds.at(-1));
  const [details,setDetails]=useState(null);
  const [evidenceState,setEvidenceState]=useState('');
  useEffect(()=>{
    if(!expanded)return;
    const controller=new AbortController();
    setEvidenceState('loading');
    api.crowding({journey_id:journey.id,date:query.date,time:query.time},controller.signal).then(data=>{
      if(!controller.signal.aborted){setDetails(data);setEvidenceState('');}
    }).catch(()=>{if(!controller.signal.aborted)setEvidenceState('error');});
    return ()=>controller.abort();
  },[expanded,journey.id,query.date,query.time]);
  const segments=journeySegments(journey,details?.segments||[]);
  return <article data-itinerary-id={journey.itineraryId} className={'journey '+(recommended?'recommended':'')}>
    <div className={"journey-main"+(labels[busiest?.level]?" has-crowding":"")}><div className="journey-route"><div className="bus-icon"><BusFront size={23}/></div><div><div className="route-line">{legs.map((leg,i)=><React.Fragment key={i}>{i>0&&<ArrowRight size={13}/>}<strong>{leg.route}</strong></React.Fragment>)}{recommended&&<span className="rec">{query.preference==='balanced'?'Balanced schedule':'Earliest arrival'}</span>}</div><div className="journey-sub">{time(journey.departure)} <span>–</span> {time(journey.arrival)} <span>·</span> {transfers?transfers+' transfer'+(transfers===1?'':'s'):'Direct bus'} </div></div></div>{labels[busiest?.level]&&<div className="journey-crowd"><Badge level={busiest.level}/><small>{stopName(busiest.from)} – {stopName(busiest.to)}</small></div>}<div className="duration"><FareLabel fare={journeyFare(journey)} total/>{journey.duration}<small> min</small>{journey.arrival>earliestArrival&&<small className="result-delta">+{journey.arrival-earliestArrival} min to arrive</small>}</div><button className="detail-btn" aria-label={expanded?'Hide journey details':'Show journey details'} aria-expanded={expanded} onClick={()=>setExpanded(!expanded)}><ChevronDown size={21} className={expanded?'rotate':''}/></button></div>
    <p className="journey-endpoints"><strong>{firstStop}</strong> → <strong>{lastStop}</strong></p>
    {!expanded&&legs.slice(1).map((leg,index)=><TransferNote key={index} previous={legs[index]} next={leg} stopName={stopName} minimumSeconds={journey.transferMinimumSeconds}/>)}
    <StopPreview journey={journey} stopName={stopName} onSelect={setWatchedStop}/>
    {watchedStop&&<StopCalls journey={journey} stopId={watchedStop} stopName={stopName} serviceDate={query.date} now={now}/>}
    <CrowdingStrip segments={segments} stopName={stopName} onSelect={segment=>onMap(journey,segment)}/>
    {expanded&&<div className="journey-details">
      <div className="detail-top"><PredictionEvidence prediction={details} loading={evidenceState==='loading'} error={evidenceState==='error'}/><button className="text-btn" onClick={()=>onMap(journey)}><MapPin size={16}/> View on map</button></div>
      <HistoricalDemand legs={legs} searchDate={query.date}/>
      <StopItinerary journey={journey} segments={segments} stopName={stopName}/>
    </div>}
  </article>;
}
function Planner({stops,stopState,reloadStops,query,setQuery,results,setResults,submitted,setSubmitted,onMap,windows,setWindows,active,setActive,now}){
  const [status,setStatus]=useState('');
  const [watchedStop,setWatchedStop]=useState('');
  const [formError,setFormError]=useState('');
  const [notice,setNotice]=useState('');
  const today = delhiDateTime(now).date;
  const [controller,setController]=useState(null);
  useEffect(()=>()=>controller?.abort(),[controller]);
  const update=(key,value)=>{controller?.abort();setFormError('');setNotice('');setResults(null);setWindows(null);setActive(0);setStatus('');setQuery(q=>({...q,[key]:value,...(key==='date'?{mode:'upcoming'}:{})}));};
  const stopNames = React.useMemo(() => new Map(stops.map(stop => [stop.id, stop.name])), [stops]);
  const stopName = id => stopNames.get(id) || id;
  async function search(e){
    e.preventDefault();
    if(status==='loading')return;
    if(!query.origin||!query.destination||query.origin===query.destination){
      setFormError('Select two different bus stops.');return;
    }
    if(!query.date||!query.time){setFormError('Enter a departure date and time.');return;}
    const current = delhiDateTime();
    if(query.date < current.date && query.mode !== 'historical'){
      setFormError('That Delhi date has passed. Select Historical timetable lookup to view it.');
      return;
    }
    const adjusted = query.mode !== 'historical' && query.date === current.date && query.time < current.time;
    const searchQuery = adjusted ? {...query,time:current.time} : query;
    if(adjusted) setQuery(searchQuery);
    setNotice(adjusted ? 'The requested time has passed. Showing upcoming departures in Delhi.' : '');
    controller?.abort();
    const request=new AbortController();
    setController(request);
    setStatus('loading');
    setSubmitted(searchQuery);
    setWatchedStop('');
    setResults(null);
    setActive(0);
    setWindows(null);
    try{
      const items=await api.journeys(searchQuery,request.signal);
      if(!request.signal.aborted){setResults(distinctJourneys(items));setStatus('');}
    }catch(error){
      if(!request.signal.aborted){
        const detail=error.response?.data?.detail;
        setStatus(typeof detail==='string'&&[404,422,429].includes(error.response?.status)
          ? detail : 'We couldn’t load journeys. Try your search again.');
      }
    }
  }
  const shown=active&&windows?.[active];
  const shownQuery=shown?.query||submitted;
  const journeys=shown?.items||results||[];
  const earliestArrival=compareJourneys(journeys).earliest?.arrival;
  const servedStops=[...new Set(journeys.flatMap(journey=>journey.legs.flatMap(leg=>leg.stopIds)))];
  const selectedStop=servedStops.includes(watchedStop)?watchedStop:servedStops.includes(shownQuery.origin)?shownQuery.origin:servedStops[0];
  return <>
    <Header scene="bus" section="JOURNEY PLANNER" title="Plan your Delhi bus trip" description="Compare scheduled journeys across Delhi. Crowd estimates are pending validation." Icon={RouteIcon}/>
    <section className="panel search-panel" aria-labelledby="search-title"><div className="section-title"><div className="section-icon"><Navigation size={20}/></div><div><h2 id="search-title">Find a journey</h2><p>Choose a departure and what matters most to you.</p></div></div>
    <form onSubmit={search}>
      <div className="fields">
        <div className="stops"><StopInput label="From" icon={MapPin} id="origin" stops={stops} value={query.origin} onPick={id=>update('origin',id)}/><button type="button" className="swap" aria-label="Swap origin and destination" onClick={()=>{controller?.abort();setResults(null);setWindows(null);setActive(0);setStatus('');setFormError('');setQuery(q=>({...q,origin:q.destination,destination:q.origin}));}}><ArrowDownUp size={18}/></button><StopInput label="To" icon={Navigation} id="destination" stops={stops} value={query.destination} onPick={id=>update('destination',id)}/></div>
        <div className="date-time"><div><label htmlFor="date">Departure date</label><div className="input-wrap"><CalendarDays size={17}/><input type="date" id="date" value={query.date} onChange={e=>update('date',e.target.value)} required/></div></div><div><label htmlFor="time">Time (IST)</label><div className="input-wrap"><Clock3 size={17}/><input type="time" id="time" value={query.time} onChange={e=>update('time',e.target.value)} required/></div></div></div>
      </div>
      <div className="form-bottom"><fieldset><legend>Journey preference</legend><div className="preferences">{preferences.map(([key,name,Icon])=><button key={key} type="button" aria-pressed={query.preference===key} onClick={()=>update('preference',key)}><Icon size={17}/>{name}</button>)}</div></fieldset><button className="primary" disabled={stopState!==''||!stops.length||status==='loading'}><Search size={18}/>{status==='loading'?'Searching…':'Find journeys'}</button></div>
      {query.date < today&&<label className="timetable-mode"><input type="checkbox" checked={query.mode==='historical'} onChange={event=>update('mode',event.target.checked?'historical':'upcoming')}/> Historical timetable lookup</label>}
      {notice&&<Message>{notice}</Message>}
      {formError&&<Message error>{formError}</Message>}{stopState==='loading'&&<Message>Loading bus stops…</Message>}{stopState==='error'&&<Message error>Bus stops could not be loaded. <button type="button" className="text-btn" onClick={reloadStops}>Try again</button></Message>}
      {stopState===''&&!stops.length&&<Message>No bus stops are available in the imported schedule.</Message>}
    </form></section>
    <Comparison journeys={journeys}/>
    {results!==null&&<DepartureOptions baseline={results} query={{...submitted,preference:query.preference}} {...{active,setActive,windows,setWindows}}/>}
    <section className="results"><div className="results-header"><div><h2>Journey options</h2><p>{results===null?'Search to see available buses.':journeys.length+' options · '+shownQuery.time+' IST · '+(shownQuery.mode==='historical'?'Historical timetable · ':'')+(query.preference==='balanced'?'Ranked by arrival plus a 10-minute transfer penalty':'Sorted by scheduled arrival')}</p></div></div>
    {status==='loading'&&<Message>Finding scheduled journeys…</Message>}{status&&status!=='loading'&&<Message error>{status}</Message>}{results!==null&&!journeys.length&&<Message>No journeys found. Try a different departure time or stop pair.</Message>}
    {servedStops.length>0&&<div className="panel watch-stop">
      <div><label htmlFor="watch-stop">Check buses at a stop</label><div className="map-stop-select"><select id="watch-stop" value={selectedStop} onChange={event=>setWatchedStop(event.target.value)}>
        {servedStops.map(id=><option key={id} value={id}>{stopName(id)}</option>)}
      </select><ChevronDown size={16} aria-hidden="true"/></div></div>
      <p>Timing for {shownQuery.date} is based on the schedule and the current time in IST. Stop images are illustrative.</p>
    </div>}
    <div className="result-list">{journeys.map((journey,i)=><JourneyCard key={submitted.origin+submitted.destination+shownQuery.date+shownQuery.time+(journey.itineraryId||journey.id)} journey={journey} earliestArrival={earliestArrival} recommended={i===0} query={shownQuery} stopName={stopName} onMap={(j,stretch)=>onMap(j,stretch,shownQuery.date)} watchedStop={selectedStop} setWatchedStop={setWatchedStop} now={now}/>)}</div>
    </section>
  </>;
}

function Analytics(){
  return <>
    <Header scene="crowd" section="NETWORK ANALYTICS" title="Explore the Delhi bus network"
      description="Scheduled departures and the busiest stop-to-stop links in the imported timetable." Icon={ChartNoAxesCombined}/>
    <Suspense fallback={<Message>Loading network analytics…</Message>}><NetworkAnalytics/></Suspense>
  </>;
}

class RouteErrorBoundary extends React.Component {
  state = {failed: false};
  static getDerivedStateFromError() { return {failed: true}; }
  render() {
    return this.state.failed
      ? <Message error>This page could not be displayed. <button className="text-btn" onClick={() => window.location.reload()}>Reload page</button></Message>
      : this.props.children;
  }
}

function App(){
  const location = useLocation();
  const [stops,setStops]=useState([]);
  const [stopState,setStopState]=useState('loading');
  const [stopAttempt,setStopAttempt]=useState(0);
  const reloadStops=()=>{setStopState('loading');setStopAttempt(value=>value+1);};
  const [query,setQuery]=useState(()=>({...initial,...delhiDateTime(),mode:'upcoming'}));
  const [results,setResults]=useState(null);
  const [submitted,setSubmitted]=useState(initial);
  const [journey,setJourney]=useState(null);
  const [serviceDate,setServiceDate]=useState(initial.date);
  const [now,setNow]=useState(Date.now);
  useEffect(()=>{const timer=setInterval(()=>setNow(Date.now()),15000);return ()=>clearInterval(timer);},[]);
  const [selectedStretch,setSelectedStretch]=useState(null);
  const [windows,setWindows]=useState(null);
  const [active,setActive]=useState(0);
  const [open,setOpen]=useState(false);
  const navigate=useNavigate();
  useEffect(()=>{const c=new AbortController();api.stops(c.signal).then(data=>{if(!c.signal.aborted){if(!Array.isArray(data))throw new Error('Unexpected response');setStops(data);setStopState('');}}).catch(()=>{if(!c.signal.aborted)setStopState('error');});return()=>c.abort();},[stopAttempt]);
  return <div className="shell"><Sidebar open={open} close={()=>setOpen(false)}/>{open&&<button className="overlay" aria-label="Close navigation" onClick={()=>setOpen(false)}/>}<div className="workspace"><header className="topbar"><button className="menu" aria-label="Open navigation" onClick={()=>setOpen(true)}><Menu size={24}/></button><div><BusFront size={17}/> Delhi public transport</div></header>
  <main><RouteErrorBoundary key={location.pathname}><Routes><Route path="/" element={<Planner {...{stops,stopState,reloadStops,query,setQuery,results,setResults,submitted,setSubmitted,windows,setWindows,active,setActive,now}} onMap={(j,stretch=null,date)=>{setJourney(j);setServiceDate(date);setSelectedStretch(stretch);navigate('/map');}}/>}/><Route path="/map" element={<Suspense fallback={<Message>Loading route explorer…</Message>}><Explorer {...{stops,journey,query,selectedStretch,serviceDate,now,Header,Message,Badge,StopInput,StopCalls,StopItinerary}}/></Suspense>}/><Route path="/analytics" element={<Analytics/>}/></Routes></RouteErrorBoundary></main></div></div>;
}
const introDuration = 1800;
const reducedMotion = '(prefers-reduced-motion: reduce)';

function Safarnama(){
  const [showIntro,setShowIntro]=useState(()=>!window.matchMedia(reducedMotion).matches);

  useEffect(()=>{
    if(!showIntro)return;
    const timer=window.setTimeout(()=>setShowIntro(false),introDuration+100);
    return ()=>window.clearTimeout(timer);
  },[showIntro]);

  return <HashRouter>
    <div inert={showIntro||undefined}><App/></div>
    {showIntro&&<div className="site-intro" aria-hidden="true" style={{'--intro-duration':introDuration+'ms'}} onAnimationEnd={event=>{
      if(event.target===event.currentTarget)setShowIntro(false);
    }}>
      <div className="site-intro-logo">
        <span className="site-intro-mark"><BusFront size={44}/></span>
        <Wordmark className="intro-wordmark"/>
      </div>
    </div>}
  </HashRouter>;
}

createRoot(document.getElementById('root')).render(<Safarnama/>);
