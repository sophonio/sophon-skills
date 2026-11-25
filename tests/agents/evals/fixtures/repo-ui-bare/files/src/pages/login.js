import { Button } from '../components/Button.js';
import { Field } from '../components/Field.js';

export function login(params) {
  const next = params.get('next') ?? '/';
  return {
    title: 'Sign in',
    body: `<h1>Sign in</h1>
<form method="post" action="/login?next=${encodeURIComponent(next)}">
${Field({ id: 'email', label: 'Email', type: 'email' })}
${Field({ id: 'password', label: 'Password', type: 'password' })}
${Button({ label: 'Sign in', type: 'submit' })}
</form>`,
  };
}
