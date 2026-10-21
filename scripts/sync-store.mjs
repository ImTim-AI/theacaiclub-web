#!/usr/bin/env node
// Snapshot the app's published Store catalogue into the website.
//
//   npm run sync-store          (needs ACAI_SUPABASE_URL + ACAI_SUPABASE_ANON_KEY,
//                                read from ../../_os/keys.env when not in env)
//
// The server stays the catalogue authority. This script reads ONLY what the app
// reads (anon key, RLS-published rows), signs the private `merch` photos, and
// writes a public copy to public/store/ plus src/data/store.json. The site is
// static, so a catalogue change goes live on the next sync + deploy.
//
// Ordering and photo selection are ported from app/lib/merch/merch_models.dart
// (defaultColour, initialGalleryFor, lookbookGalleryFor, shopCardGalleryFor)
// so a product looks the same on the web as in the app.

import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const OUT_IMG = join(ROOT, 'public', 'images', 'store');
const OUT_JSON = join(ROOT, 'src', 'data', 'store.json');

function env() {
  const vals = { ...process.env };
  const keys = resolve(ROOT, '..', '..', '_os', 'keys.env');
  if ((!vals.ACAI_SUPABASE_URL || !vals.ACAI_SUPABASE_ANON_KEY) && existsSync(keys)) {
    for (const line of readFileSync(keys, 'utf8').split('\n')) {
      const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/);
      if (m && !vals[m[1]]) vals[m[1]] = m[2].replace(/^['"]|['"]$/g, '');
    }
  }
  if (!vals.ACAI_SUPABASE_URL || !vals.ACAI_SUPABASE_ANON_KEY) {
    throw new Error('ACAI_SUPABASE_URL / ACAI_SUPABASE_ANON_KEY missing');
  }
  return { url: vals.ACAI_SUPABASE_URL.replace(/\/$/, ''), key: vals.ACAI_SUPABASE_ANON_KEY };
}

const { url: SUPA, key: ANON } = env();
const H = { apikey: ANON, Authorization: `Bearer ${ANON}` };

async function rest(path) {
  const r = await fetch(`${SUPA}/rest/v1/${path}`, { headers: H });
  if (!r.ok) throw new Error(`${path}: HTTP ${r.status} ${await r.text()}`);
  return r.json();
}

const COLUMNS =
  'id,slug,name,sort_order,' +
  'merch_products(id,slug,name,description,materials,category_id,sale_mode,expected_dispatch_at,' +
  'price_pence,default_colour,default_model,published,sort_order,' +
  'merch_variants(id,colour,size,available_qty,active),' +
  'merch_product_images(id,colour,view,model,storage_path,sort_order,is_hero))';

const SIZE_ORDER = ['XS', 'S', 'M', 'L', 'XL', 'XXL'];
const sizeRank = (s) => {
  const i = SIZE_ORDER.indexOf(String(s).toUpperCase());
  return i < 0 ? SIZE_ORDER.length : i;
};
const SWATCH = { black: '#16150E', white: '#F4F1EC', cream: '#DED9D4', sand: '#CBC8BE', pink: '#FCD4DF' };
const swatch = (c) => SWATCH[String(c).trim().toLowerCase()] ?? '#8A8A87';
const PERSON = new Set(['male', 'female']);
const otherModel = (a, b) => {
  a = (a ?? '').trim().toLowerCase();
  b = (b ?? '').trim().toLowerCase();
  return PERSON.has(a) && PERSON.has(b) && a !== b;
};
const lowestSort = (imgs) => imgs.reduce((best, i) => (!best || i.sort_order < best.sort_order ? i : best), null);
const byOrderThenName = (a, b) => (a.sort_order - b.sort_order) || a.name.localeCompare(b.name);
const pence = (p) => `£${Math.trunc(p / 100)}.${String(p % 100).padStart(2, '0')}`;

function model(p) {
  const variants = (p.merch_variants ?? [])
    .filter((v) => v.active)
    .sort((a, b) => a.colour.localeCompare(b.colour) || (sizeRank(a.size) - sizeRank(b.size)) || a.size.localeCompare(b.size));
  const images = (p.merch_product_images ?? [])
    .filter((i) => i.storage_path)
    .sort((a, b) => a.sort_order - b.sort_order);
  const colours = [...new Set(variants.map((v) => v.colour))];
  const forColour = (c) => variants.filter((v) => v.colour === c);

  let defaultColour = null;
  if (colours.length) {
    if (p.default_colour && colours.includes(p.default_colour)) defaultColour = p.default_colour;
    else defaultColour = colours.find((c) => forColour(c).some((v) => v.available_qty > 0)) ?? colours[0];
  }
  const hero = images.find((i) => i.is_hero) ?? images[0] ?? null;
  const galleryFor = (c) => (c == null ? images : images.filter((i) => i.colour == null || i.colour === c));
  const moveFirst = (list, idx) => (idx <= 0 ? list : [list[idx], ...list.slice(0, idx), ...list.slice(idx + 1)]);
  const initialGalleryFor = (c) => {
    const g = galleryFor(c);
    if (c !== defaultColour || !p.default_model) return g;
    const m = p.default_model.toLowerCase();
    return moveFirst(g, g.findIndex((i) => (i.model ?? '').trim().toLowerCase() === m));
  };
  const lookbookGalleryFor = (c) => {
    const g = initialGalleryFor(c);
    const dm = p.default_model;
    if (c === defaultColour && dm && g.length && (g[0].model ?? '').trim().toLowerCase() === dm.toLowerCase()) return g;
    if (!hero || !g.length) return g;
    return moveFirst(g, g.findIndex((i) => i.id === hero.id));
  };
  const cardGalleryFor = (c) => {
    const g = lookbookGalleryFor(c);
    if (g.length <= 1) return g;
    const [lead, ...rest] = g;
    const pair = lowestSort(rest.filter((i) => otherModel(lead.model, i.model))) ?? lowestSort(rest);
    return pair ? [lead, pair] : [lead];
  };
  return { variants, images, colours, defaultColour, forColour, initialGalleryFor, cardGalleryFor };
}

async function sign(paths) {
  const r = await fetch(`${SUPA}/storage/v1/object/sign/merch`, {
    method: 'POST',
    headers: { ...H, 'Content-Type': 'application/json' },
    body: JSON.stringify({ expiresIn: 600, paths }),
  });
  if (!r.ok) throw new Error(`sign: HTTP ${r.status}`);
  const out = {};
  for (const e of await r.json()) if (e.path && e.signedURL) out[e.path] = `${SUPA}/storage/v1${e.signedURL}`;
  return out;
}

// Public copy: resized JPEG, content-hashed name so a replaced photo never
// serves stale from a CDN or a chat app's preview cache.
async function exportImage(signedUrl, slug, storagePath) {
  const r = await fetch(signedUrl);
  if (!r.ok) throw new Error(`${storagePath}: HTTP ${r.status}`);
  const buf = Buffer.from(await r.arrayBuffer());
  const hash = createHash('sha256').update(buf).digest('hex').slice(0, 10);
  const dir = join(OUT_IMG, slug);
  mkdirSync(dir, { recursive: true });
  const name = `${hash}.jpg`;
  const tmp = join(dir, `.src-${hash}`);
  writeFileSync(tmp, buf);
  execFileSync('sips', ['-s', 'format', 'jpeg', '-s', 'formatOptions', '82', '-Z', '1400', tmp, '--out', join(dir, name)], { stdio: 'ignore' });
  rmSync(tmp);
  const dims = execFileSync('sips', ['-g', 'pixelWidth', '-g', 'pixelHeight', join(dir, name)]).toString();
  const w = Number(dims.match(/pixelWidth: (\d+)/)[1]);
  const h = Number(dims.match(/pixelHeight: (\d+)/)[1]);
  return { src: `/images/store/${slug}/${name}`, width: w, height: h };
}

const [drops, categoryRows] = await Promise.all([
  rest(`merch_drops?select=${encodeURIComponent(COLUMNS)}&status=eq.published&order=sort_order.asc`),
  rest('merch_categories?select=id,slug,name,sort_order,published&published=eq.true&order=sort_order.asc'),
]);

const raw = drops
  .sort((a, b) => a.sort_order - b.sort_order)
  .flatMap((d) => (d.merch_products ?? []).filter((p) => p.published === true).sort(byOrderThenName));

const allPaths = [...new Set(raw.flatMap((p) => (p.merch_product_images ?? []).map((i) => i.storage_path).filter(Boolean)))];
const signed = await sign(allPaths);

rmSync(OUT_IMG, { recursive: true, force: true });
const exported = {};
const products = [];
for (const p of raw) {
  const m = model(p);
  const img = async (i) => {
    const key = `${p.slug}|${i.storage_path}`;
    if (!exported[key]) {
      if (!signed[i.storage_path]) throw new Error(`no signed URL for ${i.storage_path}`);
      exported[key] = { ...(await exportImage(signed[i.storage_path], p.slug, i.storage_path)), alt: `${p.name}${i.colour ? `, ${i.colour}` : ''}${i.view ? `, ${i.view}` : ''}` };
    }
    return exported[key];
  };
  const colours = [];
  for (const c of m.colours) {
    colours.push({
      name: c,
      swatch: swatch(c),
      card: await Promise.all(m.cardGalleryFor(c).map(img)),
      gallery: await Promise.all(m.initialGalleryFor(c).map(img)),
      sizes: m.forColour(c).map((v) => ({ size: v.size, soldOut: !(v.available_qty > 0) })),
    });
  }
  const soldOut = m.variants.length > 0 && m.variants.every((v) => !(v.available_qty > 0));
  products.push({
    slug: p.slug,
    name: p.name,
    categoryId: p.category_id ?? '',
    price: pence(p.price_pence),
    pricePence: p.price_pence,
    preorder: p.sale_mode === 'preorder',
    expectedDispatchAt: p.expected_dispatch_at,
    descriptionLines: String(p.description ?? '').split('\n').map((l) => l.trim()).filter(Boolean),
    materials: p.materials?.trim() || null,
    defaultColour: m.defaultColour,
    soldOut,
    colours,
  });
}

// Only categories that hold something; the app shows honest empty tabs, but a
// static page has no reason to link to nothing.
const categories = categoryRows
  .sort(byOrderThenName)
  .filter((c) => products.some((p) => p.categoryId === c.id))
  .map((c) => ({ id: c.id, slug: c.slug, name: c.name }));

mkdirSync(dirname(OUT_JSON), { recursive: true });
writeFileSync(OUT_JSON, JSON.stringify({ syncedAt: new Date().toISOString(), categories, products }, null, 2) + '\n');
console.log(`synced ${products.length} products, ${categories.length} categories, ${Object.keys(exported).length} images`);
