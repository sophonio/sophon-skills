import { home } from './pages/home.js';
import { login } from './pages/login.js';
import { settings } from './pages/settings.js';
import { Header } from './components/Header.js';

const PAGES = { '/': home, '/login': login, '/settings': settings };

export function renderPage(path, params) {
  const page = PAGES[path];
  if (!page) return null;
  const { title, body } = page(params);
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${title} - plainboard</title>
<link rel="stylesheet" href="/src/styles/app.css">
</head>
<body>
${Header({ current: path })}
<main>
${body}
</main>
</body>
</html>
`;
}
