import { formatCount } from '../lib/format.js';

export function Card({ title, description, items }) {
  return `<article>
<h2>${title}</h2>
<p>${description}</p>
<p>${formatCount(items, 'item')}</p>
</article>`;
}
