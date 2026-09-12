import { defineConfig } from "@playwright/test";
import { existsSync } from "node:fs";
import path from "node:path";

// Node 22 carga el archivo privado local; CI puede inyectar las variables directamente.
const localEnvironment = path.resolve(__dirname, "../../.env");
if (existsSync(localEnvironment)) process.loadEnvFile(localEnvironment);

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 45000,
  expect: { timeout: 10000 },
  reporter: [["list"], ["junit", { outputFile: "../../docs/evidence/frontend-junit.xml" }]],
  use: {
    baseURL: process.env.E2E_BASE_URL || "http://localhost:3000",
    browserName: "chromium",
    viewport: { width: 1440, height: 1000 },
    // No traces/HAR: guardarían cookies y credenciales de las solicitudes.
    trace: "off",
    screenshot: "off",
    video: "off",
  },
});
