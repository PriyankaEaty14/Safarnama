import {expect, test} from '@playwright/test';

const transferPair = ['Anand Vihar ISBT', 'Shivaji Stadium Terminal'];
const directPair = ['Rohini Sec 22 Terminal', 'Rohini Sec 23 Pocket 1'];

async function pickStop(page, label, name, keyboard = false, code = null) {
  const input = page.getByLabel(label, {exact: true});
  await input.click();
  await input.fill('');
  await input.pressSequentially(name);
  await expect(input).toHaveValue(name);
  const suggestion = page.locator('.suggestions').getByRole('button', {name: code || name});
  await expect(suggestion.first()).toBeVisible();
  if (keyboard) {
    await input.press('ArrowDown');
    await page.keyboard.press('Enter');
  } else {
    await suggestion.first().click();
  }
}

async function fillSearch(page, pair) {
  await pickStop(page, 'From', pair[0], true);
  await pickStop(page, 'To', pair[1]);
  await page.getByLabel('Departure date').fill('2026-11-23');
  await page.getByLabel('Time (IST)').fill('08:35');
  const historical = page.getByLabel('Historical timetable lookup');
  if (await historical.isVisible()) await historical.check();
}

async function openPlanner(page) {
  const stops = page.waitForResponse(response => response.url().includes('/api/v1/stops?limit=10000'));
  await page.goto('/');
  const response = await stops;
  expect(response.ok()).toBe(true);
  await expect(page.getByRole('button', {name: 'Find journeys'})).toBeEnabled();
}

async function navigate(page, name) {
  const menu=page.getByRole('button',{name:'Open navigation'});
  if (await menu.isVisible()) await menu.click();
  await page.getByRole('link',{name}).click();
}

async function showMap(page, card) {
  await card.getByRole('button', {name:'Show journey details'}).click();
  const details=card.locator('.journey-details');
  await expect(details.getByText('Crowding information is unavailable because validated segment-level passenger-load data is unavailable.')).toBeVisible();
  await details.getByRole('button', {name:'View on map'}).click();
}

test.beforeEach(async ({page}) => {
  // These third-party assets are independent of itinerary geometry and can vary by network.
  await page.route(/https:\/\/(tile\.openstreetmap\.org|fonts\.(googleapis|gstatic)\.com)\//, route => route.fulfill({status:204}));
});

test('real Delhi timetable supports transfers, two mapped legs and analytics', async ({page}) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('response', response => {
    if (response.url().includes('/api/v1/') && response.status() >= 400) {
      errors.push(response.status() + ' ' + response.url());
    }
  });
  await openPlanner(page);
  await fillSearch(page, transferPair);
  await page.getByRole('button', {name:'Balanced', exact:true}).click();
  await page.getByRole('button', {name:'Find journeys'}).click();
  const card = page.locator('article.journey').filter({hasText:'1 transfer'}).first();
  await expect(card).toBeVisible();
  await showMap(page, card);
  await expect(page.getByText(/Change buses at/).first()).toBeVisible();
  await expect(page.locator('.leaflet-overlay-pane path')).toHaveCount(2);
  await expect(page.locator('.leaflet-marker-icon.marker-transfer').first()).toBeVisible();

  await navigate(page, 'Network analytics');
  await expect(page.getByRole('heading', {name:'Scheduled trip starts by hour'})).toBeVisible();
  await expect(page.getByText('80,357', {exact:true})).toBeVisible();
  await expect(page.getByText('27,37,136', {exact:true})).toBeVisible();
  await expect(page.locator('.recharts-bar-rectangle').first()).toBeVisible();
  await expect(page.getByRole('row')).toHaveCount(11);
  await expect(page.getByRole('heading', {name:'Scheduled trips by service day'})).toBeVisible();
  expect(errors).toEqual([]);
});

test('direct journeys render and the map handles unavailable geometry', async ({page}) => {
  await openPlanner(page);
  await fillSearch(page, directPair);
  await page.getByRole('button', {name:'Find journeys'}).click();
  const card = page.locator('article.journey').filter({hasText:'Direct bus'}).first();
  await expect(card).toBeVisible();
  await showMap(page, card);
  await expect(page.locator('.leaflet-overlay-pane path')).toHaveCount(1);

  await navigate(page, 'Journey planner');
  await page.route('**/api/v1/routes/*/geometry?*', route => route.fulfill({
    json:{status:'available',coordinates:[[28,77],[100,77]],shapeId:'invalid-test-shape'},
  }));
  await showMap(page, card);
  await expect(page.getByText(/Verified shape geometry is unavailable/)).toBeVisible();
  await expect(page.locator('.leaflet-overlay-pane path')).toHaveCount(0);
  await expect(page.locator('.leaflet-marker-icon.marker-origin')).toBeVisible();
});

test('planner clears swapped fields and handles validation, loading, empty results and API failure', async ({page}) => {
  await openPlanner(page);
  await pickStop(page,'From',directPair[0]);
  await page.getByRole('button',{name:'Swap origin and destination'}).click();
  await expect(page.getByLabel('From',{exact:true})).toHaveValue('');
  await expect(page.getByLabel('To',{exact:true})).toHaveValue(directPair[0]);
  await page.getByRole('button',{name:'Find journeys'}).click();
  await expect(page.getByRole('alert')).toHaveText('Select two different bus stops.');

  await fillSearch(page,directPair);
  await page.getByLabel('Departure date').fill('2041-01-01');
  let releaseRequest;
  const wait = new Promise(resolve => { releaseRequest=resolve; });
  await page.route('**/api/v1/journeys?*', async route => {
    await wait;
    await route.continue();
  }, {times:1});
  await page.getByRole('button',{name:'Find journeys'}).click();
  await expect(page.getByRole('button',{name:'Searching…'})).toBeDisabled();
  releaseRequest();
  await expect(page.getByText(/No journeys found/)).toBeVisible();

  await page.route('**/api/v1/journeys?*', route => route.fulfill({status:503, json:{detail:'Unavailable'}}));
  await page.getByRole('button',{name:'Find journeys'}).click();
  await expect(page.getByRole('alert')).toContainText('We couldn’t load journeys');
});

test('analytics can retry and displays an empty timetable', async ({page}) => {
  await page.route('**/api/v1/analytics', route => route.fulfill({status:503}), {times:1});
  await page.route('**/api/v1/analytics', route => route.fulfill({json:{
    counts:{agencies:0,stops:0,routes:0,trips:0,stopTimes:0}, scheduledDeparturesByHour:[], corridors:[],
  }}), {times:1});
  // The last registered route runs first.
  await page.goto('/#/analytics');
  await expect(page.getByText('No scheduled trip departures are available.')).toBeVisible();
  await expect(page.getByText('No scheduled corridors are available.')).toBeVisible();
  await page.reload();
  await expect(page.getByRole('alert')).toContainText('Analytics could not be loaded.');
  await page.getByRole('button',{name:'Try again'}).click();
  await expect(page.getByText('80,357',{exact:true})).toBeVisible();
});

for (const viewport of [360,390,768,820,1024,1440].map(width => ({width,height:844}))) {
  test(`planner, map and analytics fit a ${viewport.width}px viewport`, async ({page}) => {
    await page.setViewportSize(viewport);
    const fits = () => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth);
    await openPlanner(page);
    expect(await fits()).toBe(true);
    await fillSearch(page,directPair);
    await page.getByRole('button',{name:'Find journeys'}).click();
    await showMap(page,page.locator('article.journey').filter({hasText:'Direct bus'}).first());
    await expect(page.locator('.leaflet-overlay-pane path')).toHaveCount(1);
    expect(await fits()).toBe(true);
    await navigate(page,'Network analytics');
    await expect(page.getByText('80,357',{exact:true})).toBeVisible();
    expect(await fits()).toBe(true);
  });
}

test('real mapped journey shows historical demand separately from unavailable crowding', async ({page}) => {
  await openPlanner(page);
  await pickStop(page,'From','Badarpur Border');
  await page.getByLabel('To',{exact:true}).fill('Kapashera Crossing');
  await page.getByRole('button',{name:/^Kapashera Crossing · EA96DE52$/}).click();
  await page.getByLabel('Departure date').fill('2026-11-27');
  await page.getByLabel('Time (IST)').fill('08:35');
  const historicalMode = page.getByLabel('Historical timetable lookup');
  if (await historicalMode.isVisible()) await historicalMode.check();
  await page.getByRole('button',{name:'Find journeys'}).click();
  const card = page.locator('article.journey').filter({hasText:'717AUP'}).filter({hasText:'Direct bus'}).first();
  await expect(card).toBeVisible();

  let releaseRequest;
  const wait = new Promise(resolve => { releaseRequest=resolve; });
  await page.route('**/api/v1/demand/historical?*', async route => {
    await wait;
    await route.continue();
  }, {times:1});
  const fetched = page.waitForResponse(response => response.url().includes('/demand/historical?route_id=2171'));
  await card.getByRole('button',{name:'Show journey details'}).click();
  const historical = card.getByRole('region',{name:'Historical estimated ticket demand'});
  await expect(historical.getByRole('status')).toHaveText('Loading historical demand…');
  releaseRequest();
  const response = await fetched;
  expect(response.ok()).toBe(true);
  const estimate = await response.json();
  expect(estimate).toMatchObject({route:'717AUP', estimated_ticketed_passengers:82.6, is_live:false, is_actual_occupancy:false});
  await expect(historical.getByText('Friday · 08:00 IST')).toBeVisible();
  await expect(historical.getByText('82.6 estimated ticketed passengers per route-hour')).toBeVisible();
  await expect(card.getByText(/validated segment-level passenger-load data is unavailable/)).toBeVisible();
  await expect(card.locator('.crowding-strip,.itinerary-crowd')).toHaveCount(0);
  await expect(historical.getByText('Bus 717AUP · Direction UP')).toBeVisible();

  await card.getByRole('button',{name:'Hide journey details'}).click();
  await page.route('**/api/v1/demand/historical?*', route => route.fulfill({status:503}));
  await card.getByRole('button',{name:'Show journey details'}).click();
  await expect(historical.getByRole('status')).toHaveText('Historical demand could not be checked.');
  await expect(historical.getByText(/82\.6 estimated/)).toHaveCount(0);
});

test('mobile analytics displays verified Delhi historical coverage and hourly demand', async ({page}) => {
  await page.setViewportSize({width: 360, height: 800});
  await page.goto('/#/analytics');
  await expect(page.getByText('20 of 2,574 GTFS routes are mapped.')).toBeVisible();
  await page.getByLabel('Service date').fill('2026-11-27');
  await page.getByLabel('GTFS route').selectOption({label: '717AUP'});
  await expect(page.getByText('24 of 24 hourly estimates available.')).toBeVisible();
  await page.getByText('Hourly estimates table').click();
  await expect(page.getByRole('row', {name:'08:00 82.6', exact:true})).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(360);
});

test('today in Delhi advances a stale time and uses only upcoming departures', async ({page}) => {
  await openPlanner(page);
  await pickStop(page, 'From', directPair[0], true);
  await pickStop(page, 'To', directPair[1]);
  const today = await page.getByLabel('Departure date').inputValue();
  const cutoff = Math.floor((Date.now() - Date.parse(today + 'T00:00:00+05:30')) / 1000);
  await page.getByLabel('Time (IST)').fill('00:00');
  const upcoming = page.waitForResponse(response => response.url().includes('/api/v1/journeys?'));
  await page.getByRole('button', {name:'Find journeys'}).press('Enter');
  if (cutoff >= 60) await expect(page.getByText('The requested time has passed. Showing upcoming departures in Delhi.')).toBeVisible();
  const response = await upcoming;
  expect(response.ok()).toBe(true);
  const journeys = await response.json();
  for (const journey of journeys) {
    expect(journey.legs[0].departureSeconds).toBeGreaterThanOrEqual(cutoff);
  }
  await expect(page.locator('article.journey')).toHaveCount(journeys.length);
  if (!journeys.length) await expect(page.getByText(/No journeys found/)).toBeVisible();
});

test('planner avoids duplicate cards and describes the real transfer and ML coverage', async ({page}) => {
  await openPlanner(page);
  await pickStop(page, 'From', 'Anand Vihar ISBT', false, '8AF1F950');
  await pickStop(page, 'To', 'West Enclave / Sansad Vihar (T)', false, '0C3CB32B');
  await page.getByLabel('Departure date').fill('2026-11-23');
  const historical = page.getByLabel('Historical timetable lookup');
  if (await historical.isVisible()) await historical.check();
  await page.getByLabel('Time (IST)').fill('09:30');
  await page.getByRole('button', {name:'Balanced', exact:true}).click();
  let expected;
  await page.route('**/api/v1/journeys?*', async route => {
    const response = await route.fetch();
    expected = await response.json();
    await route.fulfill({response, json: [...expected, {...expected[0], id: 'duplicate-trip-id'}]});
  }, {times:1});
  await page.getByRole('button', {name:'Find journeys'}).click();
  const cards = page.locator('article.journey');
  await expect(cards.first()).toBeVisible();
  await expect(cards).toHaveCount(expected.length);
  const transfer = cards.filter({hasText:'85EXTUP'}).first();
  await expect(transfer.getByText(/Change buses at/)).toBeVisible();
  await expect(transfer.getByText(/Board bus 85EXTUP at/)).toBeVisible();
  await expect(transfer.getByText(/scheduled wait/)).toBeVisible();
  await transfer.getByRole('button', {name:'Show journey details'}).click();
  await expect(transfer.getByText(/route and direction are outside the verified historical dataset/).first()).toBeVisible();
  await expect(transfer.locator('.crowding-strip,.itinerary-crowd')).toHaveCount(0);
});
