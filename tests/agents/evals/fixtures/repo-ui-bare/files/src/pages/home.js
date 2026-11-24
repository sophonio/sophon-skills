import { Card } from '../components/Card.js';

const BOARDS = [
  { title: 'Launch', description: 'Everything for the spring launch.', items: 12 },
  { title: 'Hiring', description: 'Open roles and interviews.', items: 1 },
  { title: 'Ops', description: 'On-call and incidents.', items: 0 },
];

export function home() {
  return { title: 'Boards', body: `<h1>Boards</h1>\n${BOARDS.map(Card).join('\n')}` };
}
