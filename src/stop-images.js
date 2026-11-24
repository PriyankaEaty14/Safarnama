const illustratedStops = new Set(['anand','aksh','ito','bar','cp','lax','preet','india']);

export function stopImage(id, demo) {
  return demo && illustratedStops.has(id) ? '/images/stops/' + id + '.webp' : '/images/delhi-stop.webp';
}
