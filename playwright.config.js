import {defineConfig} from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 45_000,
  expect: {timeout: 15_000},
  use: {
    baseURL: process.env.SAFARNAMA_TEST_ORIGIN || 'http://127.0.0.1:5173',
    reducedMotion: 'reduce',
    launchOptions: {
      executablePath: process.env.SAFARNAMA_TEST_CHROMIUM || undefined,
    },
  },
});
