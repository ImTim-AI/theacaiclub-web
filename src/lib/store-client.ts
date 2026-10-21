// Browser client for web Store checkout.
//
// Card only (T, 2026-10-21): the website never sends useWallet:true, never
// reads a wallet balance and never touches points. merch-checkout prices the
// order, holds the unit and creates the PaymentIntent; this file only carries
// intent (variant, fulfilment, contact) and the signed-in user's JWT.
//
// The session lives under the same localStorage key as /order, so signing in
// on either page signs you in on both.
import { SUPABASE_ANON, SUPABASE_URL } from './public-keys';

const FN = `${SUPABASE_URL}/functions/v1`;
const AUTH = `${SUPABASE_URL}/auth/v1`;
const REST = `${SUPABASE_URL}/rest/v1`;
const SESSION_KEY = 'acai_session';

export interface Session {
  access_token: string;
  refresh_token: string;
  expires_at: number;
  email: string;
}

export class ApiError extends Error {
  code: string;
  status: number;
  constructor(message: string, code: string, status: number) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

let session: Session | null = null;

export function loadSession(): Session | null {
  try {
    const s = JSON.parse(localStorage.getItem(SESSION_KEY) || 'null');
    session = s && s.refresh_token ? s : null;
  } catch {
    session = null;
  }
  return session;
}

function saveSession() {
  try {
    if (session) localStorage.setItem(SESSION_KEY, JSON.stringify(session));
    else localStorage.removeItem(SESSION_KEY);
  } catch { /* private mode */ }
}

export function signOut() {
  session = null;
  saveSession();
}

export const currentEmail = () => session?.email ?? null;

async function authPost(path: string, body: unknown) {
  const r = await fetch(AUTH + path, {
    method: 'POST',
    headers: { apikey: SUPABASE_ANON, 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new ApiError(j.msg || j.error_description || j.error || `auth ${r.status}`, 'AUTH', r.status);
  return j;
}

/** Email a 6-digit sign-in code. No password, ever. */
export async function sendCode(email: string) {
  await authPost('/otp', { email, create_user: true });
}

export async function verifyCode(email: string, token: string) {
  const r = await authPost('/verify', { type: 'email', email, token });
  session = {
    access_token: r.access_token,
    refresh_token: r.refresh_token,
    expires_at: r.expires_at || Math.floor(Date.now() / 1000) + (r.expires_in || 3600),
    email: r.user?.email || email,
  };
  saveSession();
  return session;
}

/** A live access token, refreshed when within a minute of expiry. Null = signed out. */
export async function freshToken(): Promise<string | null> {
  if (!session) return null;
  if (session.expires_at && (session.expires_at - 60) * 1000 > Date.now()) return session.access_token;
  try {
    const r = await authPost('/token?grant_type=refresh_token', { refresh_token: session.refresh_token });
    session = {
      access_token: r.access_token,
      refresh_token: r.refresh_token,
      expires_at: r.expires_at || Math.floor(Date.now() / 1000) + (r.expires_in || 3600),
      email: session.email,
    };
    saveSession();
    return session.access_token;
  } catch {
    signOut();
    return null;
  }
}

async function invoke(fn: string, body: unknown, token: string, keepalive = false) {
  const r = await fetch(`${FN}/${fn}`, {
    method: 'POST',
    keepalive,
    headers: {
      apikey: SUPABASE_ANON,
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok || j.error || j.ok === false) {
    throw new ApiError(j.error || 'Something went wrong. Please try again.', j.code || `HTTP_${r.status}`, r.status);
  }
  return j;
}

export interface LiveVariant {
  id: string;
  colour: string;
  size: string;
  available: boolean;
  pricePence: number;
  onSale: boolean;
}

/** Live stock and price for one product, read the same way the app's catalogue
 * reads it (anon, published products only). The static page is a snapshot. */
export async function liveVariants(slug: string): Promise<LiveVariant[]> {
  const q =
    `merch_products?slug=eq.${encodeURIComponent(slug)}` +
    '&select=price_pence,published,merch_variants(id,colour,size,available_qty,active)';
  const r = await fetch(`${REST}/${q}`, {
    headers: { apikey: SUPABASE_ANON, Authorization: `Bearer ${SUPABASE_ANON}` },
  });
  if (!r.ok) throw new Error(`stock ${r.status}`);
  const rows = await r.json();
  const p = rows[0];
  if (!p) return [];
  return (p.merch_variants ?? [])
    .filter((v: any) => v.active)
    .map((v: any) => ({
      id: v.id,
      colour: v.colour,
      size: v.size,
      available: v.available_qty > 0,
      pricePence: p.price_pence,
      onSale: !!p.published,
    }));
}

export interface Pickup { id: string; name: string }

export async function pickupStores(): Promise<Pickup[]> {
  const fallback = [
    { id: '1', name: 'Reading' },
    { id: '3', name: 'Beaconsfield' },
    { id: '4', name: 'Datchet' },
  ];
  try {
    const r = await fetch(`${FN}/get-locations`, {
      method: 'POST',
      headers: { apikey: SUPABASE_ANON, Authorization: `Bearer ${SUPABASE_ANON}`, 'Content-Type': 'application/json' },
      body: '{}',
    });
    const list = await r.json();
    if (!Array.isArray(list) || !list.length) return fallback;
    return list
      .filter((l: any) => l && l.active !== false)
      .map((l: any) => ({ id: String(l.id), name: String(l.name).replace(/^The A[cç]ai Club\s*-\s*/i, '') }));
  } catch {
    return fallback;
  }
}

export interface CheckoutIntent {
  checkoutId: string;
  variantId: string;
  fulfilment: 'collection' | 'delivery';
  phone: string;
  pickupStoreId?: string;
  shipName?: string;
  shipLine1?: string;
  shipCity?: string;
  shipPostcode?: string;
}

export interface CheckoutQuote {
  orderId: string;
  orderCode: string;
  clientSecret: string;
  totalPence: number;
  cardPence: number;
  deliveryPence: number;
  fulfilment: string;
}

/** Reserve the unit and open a card PaymentIntent. Card only: useWallet is
 * always false from the website, and anything the server would charge to a
 * wallet is refused here rather than shown. */
export async function startCheckout(intent: CheckoutIntent): Promise<CheckoutQuote> {
  const token = await freshToken();
  if (!token) throw new ApiError('Sign in to buy from the shop.', 'MERCH_NOT_SIGNED_IN', 401);
  const body = {
    checkoutId: intent.checkoutId,
    variantId: intent.variantId,
    useWallet: false,
    fulfilment: intent.fulfilment,
    phone: intent.phone,
    pickupStoreId: intent.fulfilment === 'collection' ? intent.pickupStoreId : null,
    shipName: intent.fulfilment === 'delivery' ? intent.shipName : null,
    shipLine1: intent.fulfilment === 'delivery' ? intent.shipLine1 : null,
    shipCity: intent.fulfilment === 'delivery' ? intent.shipCity : null,
    shipPostcode: intent.fulfilment === 'delivery' ? intent.shipPostcode : null,
  };
  const r = await invoke('merch-checkout', body, token);
  if (r.free || !r.clientSecret || r.storedValuePence > 0 || r.cardPence !== r.totalPence) {
    // Never expected with useWallet:false. Release rather than show a split.
    if (r.orderId) await cancelCheckout(r.orderId).catch(() => {});
    throw new ApiError('We could not start a card payment. Please try again.', 'WEB_NOT_CARD_ONLY', 500);
  }
  return {
    orderId: r.orderId,
    orderCode: r.orderCode,
    clientSecret: r.clientSecret,
    totalPence: r.totalPence,
    cardPence: r.cardPence,
    deliveryPence: r.deliveryPence ?? 0,
    fulfilment: r.fulfilment,
  };
}

/** Release the held unit (the customer left or changed their details). */
export async function cancelCheckout(orderId: string, keepalive = false) {
  const token = await freshToken();
  if (!token) return;
  await invoke('merch-cancel-checkout', { orderId }, token, keepalive);
}

export const money = (p: number) => `£${Math.trunc(p / 100)}.${String(Math.abs(p) % 100).padStart(2, '0')}`;

export function uuid() {
  if (crypto.randomUUID) return crypto.randomUUID();
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
  });
}

export function track(event: string, props: Record<string, unknown> = {}) {
  try { (window as any).mixpanel?.track(event, { ...props, surface: 'web_store' }); } catch { /* analytics off */ }
}
