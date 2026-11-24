---
id: design-evaluate
summary: Page-evaluation snippets: overflow, targets, names, headings, focus, contrast pairs with the formula, a style census.
reviewed: 2026-11
---
# Measuring a page without sight: evaluate recipes

Each snippet is the body of `(() => { ... })()` inside `JSON.stringify(...)`; several can share one returned object. Run after the main content loads.

## Overflow

```js
const vw = document.documentElement.clientWidth;
const wide = [...document.querySelectorAll("body *")].filter(el => el.getBoundingClientRect().right > vw + 1);
return { viewport: vw, scrollWidth: document.documentElement.scrollWidth,
  offenders: wide.slice(0, 10).map(el => el.outerHTML.slice(0, 60)) };
```

## Target sizes

```js
const sel = "a[href],button,input,select,textarea,summary,[role=button],[role=checkbox],[role=switch],[role=tab],[role=menuitem]";
return [...document.querySelectorAll(sel)].map(el => [el, el.getBoundingClientRect()])
  .filter(([el, r]) => r.width && (r.width < 24 || r.height < 24) && getComputedStyle(el).display !== "inline")
  .slice(0, 20).map(([el, r]) => ({ el: el.outerHTML.slice(0, 80), w: Math.round(r.width), h: Math.round(r.height) }));
```

Controls under 24 x 24 CSS px; inline elements (links in text) are skipped.

## Unnamed controls

```js
const nameOf = el => (el.getAttribute("aria-label") || el.labels?.[0]?.textContent ||
  (el.getAttribute("aria-labelledby") || "").split(" ").map(i => document.getElementById(i)?.textContent || "").join("") ||
  el.textContent || el.title || el.querySelector("img[alt]")?.alt || "").trim();
const ctl = document.querySelectorAll("button,a[href],input:not([type=hidden]),select,textarea,[role=button]");
return { unnamed: [...ctl].filter(el => !nameOf(el)).slice(0, 20).map(el => el.outerHTML.slice(0, 80)),
  imgNoAlt: [...document.querySelectorAll("img:not([alt])")].slice(0, 20).map(i => i.src.slice(-60)) };
```

An approximation of the accessible name.

## Heading order

```js
const hs = [...document.querySelectorAll("h1,h2,h3,h4,h5,h6,[role=heading]")].map(h =>
  ({ level: +(h.getAttribute("aria-level") || h.tagName[1]) || 2, text: h.textContent.trim().slice(0, 50) }));
return { h1: hs.filter(h => h.level === 1).length, skips: hs.filter((h, i) => i && h.level > hs[i - 1].level + 1),
  main: document.querySelectorAll("main").length, nav: document.querySelectorAll("nav").length };
```

## Focus styles

```js
const look = el => { const s = getComputedStyle(el); return s.outlineStyle + s.outlineWidth + s.boxShadow + s.borderColor; };
const none = [];
for (const el of [...document.querySelectorAll("a[href],button,input,select,textarea,[tabindex='0']")].slice(0, 40)) {
  const before = look(el); el.focus({ preventScroll: true }); if (look(el) === before) none.push(el.outerHTML.slice(0, 80));
}
document.activeElement?.blur(); return { noVisibleFocus: none };
```

Script focus usually matches `:focus-visible` if no pointer came first; confirm by keyboard.

## Contrast pairs

WCAG 2, as coded below: linearise each channel, L = 0.2126 R + 0.7152 G + 0.0722 B, ratio = (L1 + 0.05)/(L2 + 0.05).

```js
const rgb = s => (s.match(/[\d.]+/g) || []).map(Number);
const lin = c => (c /= 255) <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
const lum = ([r, g, b]) => 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
const bgOf = el => { for (let e = el; e; e = e.parentElement) { const s = getComputedStyle(e);
  if (s.backgroundImage !== "none") return null; const c = rgb(s.backgroundColor); if (c.length === 3 || c[3] > 0) return c; }
  return [255, 255, 255]; };
const seen = {}, low = [];
for (const el of document.querySelectorAll("body *")) {
  if (![...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) continue;
  const s = getComputedStyle(el), fg = rgb(s.color), bg = bgOf(el), key = s.color + " on " + (bg || "image");
  if (seen[key]) continue; seen[key] = 1;
  if (!bg) { low.push({ key, ratio: "unknown" }); continue; }
  const a = fg[3] ?? 1, mixed = [0, 1, 2].map(i => fg[i] * a + bg[i] * (1 - a));
  const [hi, lo] = [lum(mixed), lum(bg)].sort((x, y) => y - x), ratio = (hi + 0.05) / (lo + 0.05);
  const px = parseFloat(s.fontSize), large = px >= 24 || (px >= 18.66 && Number(s.fontWeight) >= 700);
  if (ratio < (large ? 3 : 4.5)) low.push({ key, ratio: ratio.toFixed(2), px });
}
return low.slice(0, 30);
```

A translucent background counts as opaque here; recheck such pairs composited.

## Census

```js
const PRIMARY = "rgb(79, 70, 229)"; // set it to the page's primary fill
const count = {}, add = (k, v) => { (count[k] ||= {})[v] = (count[k][v] || 0) + 1; };
for (const el of document.querySelectorAll("body *")) { const s = getComputedStyle(el);
  add("fontSize", s.fontSize); add("radius", s.borderRadius); add("shadow", s.boxShadow);
  add("color", s.color); add("background", s.backgroundColor); add("duration", s.transitionDuration); }
const pick = f => Object.fromEntries(Object.entries(count).map(([k, v]) => [k, f(v)]));
return { distinct: pick(v => Object.keys(v).length), once: pick(v => Object.keys(v).filter(x => v[x] === 1)),
  primaryActions: [...document.querySelectorAll("button,a")].filter(b => getComputedStyle(b).backgroundColor === PRIMARY).length };
```

A value used once is usually off the scale.
