import {expect, test} from '@playwright/test';

const transferPair = ['Anand Vihar ISBT', 'Shivaji Stadium Terminal'];
const directPair = ['Rohini Sec 22 Terminal', 'Rohini Sec 23 Pocket 1'];

async function pickStop(page, label, name, keyboard = false) {
  const input = page.getByLabel(label, {exact: true});
  await input.click();
  await input.fill('');
  await input.pressSequentially(name);
  await expect(input).toHaveValue(name);
  const suggestion = page.locator('.suggestions').getByRole('button', {name: new RegExp('^'+name)});
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
  await expect(details.getByText('Validated trip-segment occupancy predictions are not available.')).toBeVisible();
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

for (const viewport of [{width:390,height:844},{width:820,height:1180}]) {
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
  await expect(card.getByText('Crowding information unavailable for this segment.')).toBeVisible();

  await card.getByRole('button',{name:'Hide journey details'}).click();
  await page.route('**/api/v1/demand/historical?*', route => route.fulfill({status:503}));
  await card.getByRole('button',{name:'Show journey details'}).click();
  await expect(historical.getByRole('status')).toHaveText('Historical demand could not be checked.');
  await expect(historical.getByText(/82\.6 estimated/)).toHaveCount(0);
});
