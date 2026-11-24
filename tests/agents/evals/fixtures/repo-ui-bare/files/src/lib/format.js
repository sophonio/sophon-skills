export function formatCount(count, noun) {
  return `${count} ${noun}${count === 1 ? '' : 's'}`;
}

export function formatDuration(minutes) {
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return hours > 0 ? `${hours} h ${rest} min` : `${rest} min`;
}
