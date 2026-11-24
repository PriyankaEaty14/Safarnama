import axios from 'axios';
const baseURL=import.meta.env.VITE_API_BASE_URL||'/api/v1';
const client=axios.create({baseURL,timeout:12000});
const paths={stops:import.meta.env.VITE_STOPS_PATH||'/stops',journeys:import.meta.env.VITE_JOURNEYS_PATH||'/journeys',crowding:import.meta.env.VITE_CROWDING_PATH||'/crowding',historicalDemand:import.meta.env.VITE_HISTORICAL_DEMAND_PATH||'/demand/historical',demandCoverage:'/demand/coverage',demandProfile:'/demand/profile',analytics:import.meta.env.VITE_ANALYTICS_PATH||'/analytics',routes:import.meta.env.VITE_ROUTES_PATH||'/routes'};
async function get(key,params,signal) {
  return (await client.get(paths[key],{params,signal})).data;
}
export const api={
  stops:signal=>get('stops',{limit:10000},signal),
  searchStops:(q,signal)=>get('stops',{q,limit:8},signal),
  journeys:(query,signal)=>get('journeys',query,signal),
  crowding:(query,signal)=>get('crowding',query,signal),
  historicalDemand:(query,signal)=>get('historicalDemand',query,signal),
  demandCoverage:(query,signal)=>get('demandCoverage',query,signal),
  demandProfile:(query,signal)=>get('demandProfile',query,signal),
  analytics:signal=>get('analytics',undefined,signal),
  routes:async (journey,signal)=>({legs:await Promise.all(journey.legs.map(async leg=>{
    const {data}=await client.get(`${paths.routes}/${encodeURIComponent(leg.routeId)}/geometry`,{params:{trip_id:leg.tripId,from_stop_sequence:leg.boardSequence,to_stop_sequence:leg.alightSequence},signal});
    return data;
  }))}),
};
