// @ts-check
const { defineConfig, devices } = require('@playwright/test');
require('dotenv').config({ path: '_secrets/.env.test' });

const BASE_URL = process.env.DEPLOY_TARGET || 'http://localhost:3001';

module.exports = defineConfig({
  testDir: './tests',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['list'],
  ],
  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'off',
    headless: true,
    // Hub SPA는 Supabase 세션 없이도 비인증 상태로 테스트 가능
    ignoreHTTPSErrors: true,
  },
  projects: [
    {
      name: 'mock',
      use: {
        ...devices['Desktop Chrome'],
        // 테스트용 로컬 서버 (serve로 기동)
        baseURL: process.env.DEPLOY_TARGET || 'http://localhost:3001',
        // Supabase를 실제 호출하지 않도록 스토리지 주입
        storageState: undefined,
      },
    },
    {
      name: 'realdb',
      use: {
        ...devices['Desktop Chrome'],
        baseURL: process.env.DEPLOY_TARGET || 'https://test.worksfree.kr',
      },
    },
  ],
  // 로컬 개발 서버 자동 기동 (mock 프로젝트에서만)
  webServer: process.env.DEPLOY_TARGET
    ? undefined
    : {
        command: 'npx serve . -p 3001 -s',
        url: 'http://localhost:3001',
        reuseExistingServer: true,
        timeout: 15000,
      },
});
