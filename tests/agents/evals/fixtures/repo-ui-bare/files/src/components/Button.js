export function Button({ label, type = 'button' }) {
  return `<button type="${type}">${label}</button>`;
}
