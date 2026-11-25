import { Button } from '../components/Button.js';
import { Field } from '../components/Field.js';

export function settings() {
  return {
    title: 'Preferences',
    body: `<h1>Preferences</h1>
<form>
${Field({ id: 'display-name', label: 'Display name', value: 'Ada' })}
${Field({ id: 'timezone', label: 'Time zone', value: 'Europe/Berlin' })}
${Button({ label: 'Save', type: 'submit' })}
</form>`,
  };
}
