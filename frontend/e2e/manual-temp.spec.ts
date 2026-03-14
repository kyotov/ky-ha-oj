import { test, expect } from '@playwright/test'

test('bump all manual temperatures +1°F and restore', async ({ page }) => {
  await page.goto('/')

  // Wait for thermostat cards to load
  await expect(page.locator('text=Manual SP').first()).toBeVisible({ timeout: 15000 })

  // Read the current manual SP from the first card
  const manualSPText = await page.locator('text=Manual SP').first()
    .locator('xpath=following-sibling::span')
    .textContent()
  const currentTemp = parseFloat(manualSPText ?? '68')
  console.log(`Current manual SP: ${currentTemp}°F`)

  // --- Set to current + 1 ---
  await page.getByRole('button', { name: /⚙ All/ }).click()
  await page.getByRole('button', { name: 'Manual' }).click()

  const input = page.locator('input[type="number"]').first()
  await input.fill(String(currentTemp + 1))

  // Intercept the API response so we can inspect it
  const [response] = await Promise.all([
    page.waitForResponse('**/thermostats/all/manual'),
    page.getByRole('button', { name: 'Set' }).click(),
  ])

  const body = await response.json()
  const newManualSP = body.thermostats?.[0]?.manual_temperature_f
  console.log(`API returned manual SP: ${newManualSP}°F`)
  console.log(`Results: ${JSON.stringify(body.results)}`)

  expect(response.status()).toBe(200)
  expect(newManualSP).toBeCloseTo(currentTemp + 1, 1)

  // Wait for the card to reflect the new value
  await expect(page.locator('text=Manual SP').first()
    .locator('xpath=following-sibling::span'))
    .toHaveText(`${(currentTemp + 1).toFixed(1)}°F`, { timeout: 15000 })

  console.log(`Card shows ${currentTemp + 1}°F ✓`)

  // --- Restore original ---
  await page.getByRole('button', { name: 'Manual' }).click()
  await input.fill(String(currentTemp))

  const [response2] = await Promise.all([
    page.waitForResponse('**/thermostats/all/manual'),
    page.getByRole('button', { name: 'Set' }).click(),
  ])

  expect(response2.status()).toBe(200)

  await expect(page.locator('text=Manual SP').first()
    .locator('xpath=following-sibling::span'))
    .toHaveText(`${currentTemp.toFixed(1)}°F`, { timeout: 15000 })

  console.log(`Restored to ${currentTemp}°F ✓`)
})
