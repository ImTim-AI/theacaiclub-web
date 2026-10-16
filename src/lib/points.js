// Wire contract mirrors app-points-normal-ui/lib/points/points_contract.dart.
export const unavailable = 'Points are unavailable right now. Please try again later.';
export const notConfirmed = 'We could not apply your points rewards, so nothing has been charged. Please try again.';
export const xorCoupon = 'You can use points rewards or a discount code on this order, but not both.';
export const belowCardMinimum = 'Card payments must be at least 30p. Remove a points reward or add an item.';
// Stripe refuses a card charge between 1p and 29p (the backend's giftFloorAdjust).
export const CARD_MINIMUM_PENCE = 30;
export const earnedPoints = pounds => Math.floor((Math.round(pounds * 100) + 5) / 10);
const ids = value => value == null || (Array.isArray(value) && value.every(Number.isInteger));
export function parseLevels(raw) {
  if (!Array.isArray(raw) || !raw.every(r => r && Number.isInteger(r.cost) && r.cost > 0 &&
    typeof r.label === 'string' && r.label.trim() && ids(r.productIds) && ids(r.departmentIds) &&
    ids(r.excludeProductIds) && (r.excludeName == null || typeof r.excludeName === 'string'))) return [];
  return raw;
}
export function parseStatus(s) {
  if (!s || s.live !== true || !Number.isInteger(s.balance) || !Number.isInteger(s.available) || !Array.isArray(s.rewards)) return null;
  if (!s.rewards.every(r => r && typeof r === 'object' && !Array.isArray(r))) return null;
  const rewards = s.rewards.filter(r => r.kind === 'category');
  if (!rewards.every(r => typeof r.id === 'string' && r.id && Number.isInteger(r.pointsCost) && r.pointsCost > 0 &&
    ids(r.eligibility?.productIds) && ids(r.eligibility?.departmentIds) && ids(r.eligibility?.excludeProductIds)) ||
    new Set(rewards.map(r => r.id)).size !== rewards.length) return null;
  return {...s, rewards};
}
// Same rule as the server's covers() (points-redeem.ts, plus backend #81):
// excludeProductIds wins, then a product id match, then a non-zero department.
const covers = (r, line) => !(r.excludeProductIds || []).includes(line.pid) &&
  ((r.productIds || []).includes(line.pid) || (!!line.departmentId && (r.departmentIds || []).includes(line.departmentId)));
// The server matches excludeName against its own product name; the menu name
// is checked too, so a mismatch can only hide an offer, never add one.
const excludedByName = (excludeName, line) => !!excludeName &&
  [line.n, line.serverName].some(n => typeof n === 'string' && n.toLowerCase().includes(excludeName.toLowerCase()));
export function levelFor(line, levels) {
  const matches = levels.filter(r => covers(r, line) && !excludedByName(r.excludeName, line));
  return matches.length === 1 ? matches[0] : null;
}
export function selection(lines, levels) {
  const rewards = [];
  lines.forEach((line, lineIndex) => {
    if (!line.pointsUnits) return;
    const level = levelFor(line, levels);
    if (!level || level.label !== line.pointsLabel || level.cost !== line.pointsEach ||
      !Number.isInteger(line.pointsUnits) || line.pointsUnits < 1 || line.pointsUnits > line.q) throw new Error(notConfirmed);
    rewards.push({lineIndex, productId: line.pid, departmentId: line.departmentId ?? null, names: [line.n, line.serverName],
      levelLabel: level.label, units: line.pointsUnits, pointsEach: level.cost});
  });
  return {rewards, totalPoints: rewards.reduce((n, r) => n + r.units * r.pointsEach, 0)};
}
export function bindRewards(request, status) {
  if (!status || status.available < request.totalPoints) throw new Error(notConfirmed);
  const used = {};
  const rewards = request.rewards.map(line => {
    const target = {pid: line.productId, departmentId: line.departmentId, n: line.names?.[0], serverName: line.names?.[1]};
    const matches = status.rewards.filter(r => r.name === line.levelLabel && r.pointsCost === line.pointsEach &&
      covers(r.eligibility || {}, target) && !excludedByName(r.excludeName, target));
    const r = matches[0];
    if (matches.length !== 1 || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(r.id)) throw new Error(notConfirmed);
    used[r.id] = (used[r.id] || 0) + line.units;
    if (r.repeatable === false && used[r.id] > 1) throw new Error(notConfirmed);
    return {lineIndex: line.lineIndex, productId: line.productId, rewardId: r.id, units: line.units, pointsEach: line.pointsEach};
  });
  return {rewards, totalPoints: request.totalPoints};
}
export function reservationConfirmed(request, response, discounts) {
  const p = response?.points;
  if (!p || p.reserved !== true || p.pointsReserved !== request.totalPoints || !Array.isArray(p.items) || p.items.length !== request.rewards.length) return false;
  const remaining = [...request.rewards];
  for (const item of p.items) {
    if (!item) return false;
    const i = remaining.findIndex(r => item.lineIndex === r.lineIndex && item.rewardId === r.rewardId &&
      item.units === r.units && item.pointsCost === r.units * r.pointsEach);
    if (i < 0 || !Number.isInteger(item.discountPence) || item.discountPence < 0 || item.discountPence !== discounts[item.lineIndex]) return false;
    remaining.splice(i, 1);
  }
  return !remaining.length;
}

// get-timeslots hands out UK wall-clock stamped into the UTC part. order-pay
// converts it to a true instant before saving delivery_time; create-payment-intent
// takes delivery_time as-is, so the website converts it the same way first.
// Port of order-pay ukOffsetMinutes / ukWallIsoToInstant. The offset is read
// with formatToParts rather than by re-parsing a locale string, which not
// every browser parses.
const ukParts = new Intl.DateTimeFormat('en-GB', {timeZone: 'Europe/London', hourCycle: 'h23',
  year: 'numeric', month: 'numeric', day: 'numeric', hour: 'numeric', minute: 'numeric', second: 'numeric'});
function ukOffsetMinutes(atMs) {
  const p = Object.fromEntries(ukParts.formatToParts(new Date(atMs)).map(x => [x.type, Number(x.value)]));
  const wall = Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute, p.second);
  return Math.round((wall - Math.floor(atMs / 1000) * 1000) / 60000);
}
export function ukWallIsoToInstant(wallIso) {
  const t = new Date(wallIso);
  if (isNaN(t.getTime())) return null;
  let instant = t.getTime() - ukOffsetMinutes(t.getTime()) * 60000;
  instant = t.getTime() - ukOffsetMinutes(instant) * 60000;
  return new Date(instant);
}
// The delivery_time order-pay would save for the same pickup choice.
export function deliveryTimeFor(pickup, now = Date.now()) {
  if (pickup.slotIso) {
    const d = ukWallIsoToInstant(pickup.slotIso);
    if (!d) throw new Error('That pickup time is no longer available. Please pick a new time.');
    return d.toISOString();
  }
  return new Date(now + (pickup.mode === 'in_store' ? 5 : 15) * 60000).toISOString();
}

// Same app order fields, built from the website's authoritative quote.
export function paymentBody({quote, request, userId, email, notes, deliveryTime, id}) {
  const discounts = {};
  request.rewards.forEach(r => { discounts[r.lineIndex] = Math.round(quote.lines[r.lineIndex].basePrice * 100) * r.units; });
  const discount = Object.values(discounts).reduce((a, b) => a + b, 0);
  const amount = Math.round(quote.total * 100) - discount;
  if (!Number.isInteger(userId) || userId <= 0 || amount < 0 || !Number.isInteger(amount)) throw new Error(notConfirmed);
  if (amount > 0 && amount < CARD_MINIMUM_PENCE) throw new Error(belowCardMinimum);
  const order = {
    id, service_type: 'collection', location_id: quote.locationId, catalogue_id: quote.catalogueId,
    discountAmount: discount / 100, discontPercentage: 0, serviceChargesRate: 0,
    serviceChargesAmount: 0, deliveryChargesAmount: 0, delivery_time: deliveryTime,
    customerNotes: notes, storeType: 'Website',
    items: quote.lines.map((l, i) => ({
      product_name: l.name, ref: l.productId, rate: String(l.unitPrice), quantity: String(l.quantity),
      subtotal: l.subtotal, discountPercentage: 0, discountAmount: (discounts[i] || 0) / 100,
      saleTaxId: l.saleTaxId ?? 0, taxRate: 0, taxAmount: 0, serviceChargeExempt: 0,
      serviceChargePercentage: 0, serviceChargeAmount: 0, taxIncluded: 1,
      netAmount: (Math.round(l.subtotal * 100) - (discounts[i] || 0)) / 100,
      customerNotes: notes, departmentId: l.departmentId ?? 0,
      options: l.modifiers.map(m => ({id: m.id, name: m.name, price: m.price, quantity: 1, saleTaxId: m.saleTaxId})),
    })),
    payment: {type: 'card', amount: amount / 100, currency: 'GBP'},
    customer: {id: String(userId), email, first_name: '', last_name: '', phone: '', address_1: '', address_2: '',
      postal_code: '', city: '', state: '', latitude: '', longitude: '', delivery_notes: '', sms_marketing: 0, email_marketing: 0},
  };
  return {body: {order, amount, currency: 'GBP', userId, clientCapabilities: ['points_v1'], points: request}, discounts};
}
