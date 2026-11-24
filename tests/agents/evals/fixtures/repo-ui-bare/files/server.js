import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { extname, join, normalize } from 'node:path';
import { renderPage } from './src/main.js';

const PORT = Number(process.env.PORT ?? 4173);
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml' };
const PROTECTED = new Set(['/settings']);

function signedIn(request) {
  return (request.headers.cookie ?? '').split(';').some((part) => part.trim() === 'session=ok');
}

async function sendFile(response, path) {
  try {
    const body = await readFile(join(process.cwd(), normalize(path).replace(/^([/\\])+/, '')));
    response.writeHead(200, { 'Content-Type': TYPES[extname(path)] ?? 'application/octet-stream' });
    response.end(body);
  } catch {
    response.writeHead(404).end('not found');
  }
}

createServer(async (request, response) => {
  const url = new URL(request.url, `http://localhost:${PORT}`);
  if (request.method === 'POST' && url.pathname === '/login') {
    const next = url.searchParams.get('next') ?? '/';
    response.writeHead(303, { 'Set-Cookie': 'session=ok; Path=/; HttpOnly', Location: next.startsWith('/') ? next : '/' });
    return response.end();
  }
  if (PROTECTED.has(url.pathname) && !signedIn(request)) {
    response.writeHead(302, { Location: `/login?next=${encodeURIComponent(url.pathname)}` });
    return response.end();
  }
  if (url.pathname.startsWith('/landing/') || url.pathname.startsWith('/src/')) {
    return sendFile(response, url.pathname.endsWith('/') ? `${url.pathname}index.html` : url.pathname);
  }
  const html = renderPage(url.pathname, url.searchParams);
  response.writeHead(html ? 200 : 404, { 'Content-Type': 'text/html; charset=utf-8' });
  response.end(html ?? 'not found');
}).listen(PORT, () => console.log(`plainboard on http://localhost:${PORT}`));
