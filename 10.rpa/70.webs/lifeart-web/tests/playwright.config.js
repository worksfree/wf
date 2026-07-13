// @ts-check
const { defineConfig, devices } = require('@playwright/test');

// 대상: 기본 pre-test (검수용). PW_BASE 로 재정의 가능.
const BASE_URL = process.env.PW_BASE || 'https://pre-test-lifeart.lifeart.ai.kr';

module.exports = defineConfig({
  testDir: '.',
  fullyParallel: false,
  workers: 1,
  timeout: 90_000,           // 토스 결제창 왕복 여유
  reporter: [['list'], ['html', { outputFolder: 'playwright-report', open: 'never' }]],
  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    ignoreHTTPSErrors: true,
    // 시연(headed)에서 자동 주행이 눈에 보이도록 약간 느리게
    launchOptions: { slowMo: process.env.DEMO ? 450 : 0 },
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
});
