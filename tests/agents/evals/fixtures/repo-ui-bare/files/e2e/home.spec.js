import { test, expect } from '@playwright/test';

test('the home page lists the boards', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1, name: 'Boards' })).toBeVisible();
  await expect(page.getByRole('article')).toHaveCount(3);
});
