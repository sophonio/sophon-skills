const LINKS = [
  { href: '/', label: 'Boards' },
  { href: '/settings', label: 'Settings' },
];

export function Header({ current }) {
  const items = LINKS.map(({ href, label }) =>
    `<li><a href="${href}"${href === current ? ' aria-current="page"' : ''}>${label}</a></li>`).join('');
  return `<header><a href="/">plainboard</a><nav><ul>${items}</ul></nav></header>`;
}
