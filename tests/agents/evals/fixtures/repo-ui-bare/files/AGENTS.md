# plainboard

A small web app for tracking team boards: a home page, a settings page behind a login, and a
marketing landing page.

## Commands

- Unit tests: `npm test` (node --test, no install needed)
- End-to-end tests: `npm run e2e` (Playwright; needs `npm install` and the app running)
- App: `npm start`, then open http://localhost:4173

## Layout

- `src/components/`: components that return markup strings.
- `src/pages/`: one module per page.
- `src/lib/`: helpers with unit tests in `test/`.
- `e2e/`: Playwright specs.
- `landing/index.html`: the landing page, served at `/landing/`.
