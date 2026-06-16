// @ts-check
const { defineConfig, devices } = require('@playwright/test');

const isRealDb = process.env.PLAYWRIGHT_PROJECT === 'realdb';

module.exports = defineConfig({
  testDir: './tests',
  fullyParallel: !isRealDb,   // realdb는 순차 실행 (DB 상태 충돌 방지)
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: isRealDb ? 1 : undefined,
  reporter: [['html', { open: 'never' }], ['list']],

  use: {
    baseURL: 'http://localhost:3001',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      // ── Layer 1: Mock 테스트 (기본, 빠름) ───────────────────
      // 실행: npx playwright test
      name: 'mock',
      use: { ...devices['Desktop Chrome'] },
      testMatch: /(?<!\.realdb)\.spec\.js$/,
    },
    {
      // ── Layer 2: 실제 DB 테스트 (선택적, 느림) ──────────────
      // 실행: PLAYWRIGHT_PROJECT=realdb npx playwright test --project=realdb
      // 조건: .env.test 파일에 TEST_SUPABASE_* 환경변수 필요
      name: 'realdb',
      use: { ...devices['Desktop Chrome'] },
      testMatch: /\.realdb\.spec\.js$/,
    },
  ],

  // globalSetup/Teardown은 realdb 실행 시에만 적용
  ...(isRealDb && {
    globalSetup:    './tests/global-setup.js',
    globalTeardown: './tests/global-teardown.js',
  }),

  webServer: {
    command: 'npx serve . -p 3001 --no-clipboard',
    url: 'http://localhost:3001',
    reuseExistingServer: !process.env.CI,
    timeout: 15 * 1000,
    stdout: 'ignore',
    stderr: 'pipe',
  },
});
