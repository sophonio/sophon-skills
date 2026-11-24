export function Field({ id, label, type = 'text', value = '' }) {
  return `<p><label for="${id}">${label}</label> <input id="${id}" name="${id}" type="${type}" value="${value}"></p>`;
}
