import { expect, test, type Page } from "@playwright/test";
import path from "node:path";
import { mkdir } from "node:fs/promises";

const adminEmail = process.env.E2E_ADMIN_EMAIL || process.env.ADMIN_INITIAL_EMAIL;
const adminPassword = process.env.E2E_ADMIN_PASSWORD || process.env.ADMIN_INITIAL_PASSWORD;
const viewerEmail = process.env.E2E_VIEWER_EMAIL || process.env.VIEWER_INITIAL_EMAIL;
const viewerPassword = process.env.E2E_VIEWER_PASSWORD || process.env.VIEWER_INITIAL_PASSWORD;
if (!adminEmail || !adminPassword || !viewerEmail || !viewerPassword) {
  throw new Error("Configura las cuatro variables E2E_ADMIN/VIEWER_EMAIL/PASSWORD o ADMIN/VIEWER_INITIAL_EMAIL/PASSWORD en .env.");
}
const mutations = { "X-Requested-With": "AulaData" };
async function capture(page: Page, name: string) {
  if (process.env.E2E_CAPTURE !== "1") return;
  const folder = path.resolve(__dirname, "../../../docs/evidence");
  await mkdir(folder, { recursive: true });
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: path.join(folder, `${name}.png`), fullPage: true, animations: "disabled" });
}
async function login(page: Page, role: "ADMIN" | "VIEWER" = "ADMIN") {
  await page.goto("/login");
  await page.getByLabel("Correo electrónico").fill(role === "ADMIN" ? adminEmail! : viewerEmail!);
  await page.getByLabel("Contraseña", { exact: true }).fill(role === "ADMIN" ? adminPassword! : viewerPassword!);
  await page.getByRole("button", { name: "Iniciar sesión", exact: true }).click();
  await expect(page).toHaveURL(/\/aulas$/);
  await expect(page.getByRole("heading", { name: "Gestión de aulas", exact: true })).toBeVisible();
  await expect(page.getByText(/Mostrando|0 aulas encontradas/)).toBeVisible();
}

test("sesión requerida, login incorrecto y metadatos runtime", async ({ page }) => {
  await page.goto("/aulas");
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByText(/Commit /)).toBeVisible();
  await capture(page, "01-login");
  await page.getByLabel("Correo electrónico").fill(adminEmail!);
  await page.getByLabel("Contraseña", { exact: true }).fill("incorrecta-de-prueba");
  await page.getByRole("button", { name: "Iniciar sesión", exact: true }).click();
  await expect(page.getByRole("alert").filter({ hasText: "El correo o la contraseña no son correctos" })).toBeVisible();
  const health = await page.request.get("/health");
  expect(health.status()).toBe(200);
  expect(await health.json()).toMatchObject({ status: "ok", service: "auladata-api" });
  expect((await page.request.get("/ready")).status()).toBe(200);
  await page.goto("/health");
  await capture(page, "09-health");
});

test("ADMIN crea, consulta, edita, filtra y da de baja; persiste tras recargar", async ({ page }) => {
  await login(page);
  await capture(page, "02-aulas-admin");
  const cookie = (await page.context().cookies()).find(cookie => cookie.name === "auladata_session");
  expect(cookie?.httpOnly).toBe(true);
  expect(cookie?.sameSite).toBe("Lax");
  expect(await page.evaluate(() => window.localStorage.length)).toBe(0);
  const code = `E2E-${Date.now().toString(36).toUpperCase()}`;
  let id: number | undefined;
  try {
    await page.getByRole("link", { name: "Nueva aula", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Registrar nueva aula" })).toBeVisible();
    await page.getByLabel("Clave del aula").fill(code);
    await page.getByLabel("Nombre", { exact: true }).fill("Laboratorio de Infraestructura");
    await page.getByLabel("Edificio", { exact: true }).fill("Edificio K");
    await page.getByLabel("Capacidad", { exact: true }).fill("32");
    await page.getByLabel("Tipo de aula").selectOption("LABORATORIO");
    await capture(page, "03-nueva-aula");
    await page.getByRole("button", { name: "Registrar aula", exact: true }).click();
    await expect(page).toHaveURL(/\/aulas\/\d+\?saved=created/);
    id = Number(new URL(page.url()).pathname.split("/").at(-1));
    await expect(page.getByRole("status")).toContainText("se registró correctamente");
    await page.reload();
    await expect(page.getByRole("heading", { name: "Laboratorio de Infraestructura" })).toBeVisible();
    await expect(page.getByText("32 personas")).toBeVisible();
    await capture(page, "04-detalle-aula");
    await page.getByRole("link", { name: "Editar aula", exact: true }).click();
    await expect(page.getByLabel("Nombre", { exact: true })).toHaveValue("Laboratorio de Infraestructura");
    await page.getByLabel("Capacidad", { exact: true }).fill("36");
    await page.getByLabel("Estado", { exact: true }).selectOption("MANTENIMIENTO");
    await capture(page, "05-editar-aula");
    await page.getByRole("button", { name: "Guardar cambios", exact: true }).click();
    await expect(page.getByText("36 personas")).toBeVisible();
    await expect(page.getByText("Mantenimiento", { exact: true })).toBeVisible();
    await page.getByRole("link", { name: "Volver a las aulas", exact: true }).click();
    await page.getByLabel("Buscar aulas").fill(code);
    await expect(page.getByRole("link", { name: code, exact: true })).toBeVisible();
    await page.getByLabel("Estado", { exact: true }).selectOption("ACTIVA");
    await expect(page.getByText("No encontramos aulas con estos filtros")).toBeVisible();
    await page.getByLabel("Estado", { exact: true }).selectOption("MANTENIMIENTO");
    await expect(page.getByRole("link", { name: code, exact: true })).toBeVisible();
    await page.getByRole("button", { name: `Dar de baja ${code}`, exact: true }).click();
    await capture(page, "06-confirmacion-baja");
    await page.getByRole("button", { name: "Cancelar", exact: true }).click();
    await expect(page.getByRole("dialog")).not.toBeVisible();
    expect((await page.request.get(`/api/v1/classrooms/${id}`)).status()).toBe(200);
    await page.getByRole("button", { name: `Dar de baja ${code}`, exact: true }).click();
    await page.getByRole("button", { name: "Dar de baja", exact: true }).click();
    await expect(page.getByText("No encontramos aulas con estos filtros")).toBeVisible();
    expect((await page.request.get(`/api/v1/classrooms/${id}`)).status()).toBe(404);
  } finally { if (id) await page.request.delete(`/api/v1/classrooms/${id}`, { headers: mutations }); }
});

test("validación de clave duplicada y capacidad desde el formulario", async ({ page }) => {
  await login(page);
  const code = `DUP-${Date.now().toString(36).toUpperCase()}`;
  const input = { clave: code, nombre: "Aula de validación", edificio: "Pruebas", capacidad: 20, tipo: "TEORICA", estado: "ACTIVA" };
  const created = await page.request.post("/api/v1/classrooms", { headers: mutations, data: input });
  expect(created.status()).toBe(201);
  const { id } = await created.json();
  try {
    await page.goto("/aulas/nueva");
    await page.getByLabel("Clave del aula").fill(code);
    await page.getByLabel("Nombre", { exact: true }).fill(input.nombre);
    await page.getByLabel("Edificio", { exact: true }).fill(input.edificio);
    await page.getByLabel("Capacidad", { exact: true }).fill("0");
    expect(await page.getByLabel("Capacidad", { exact: true }).evaluate((element: HTMLInputElement) => element.validity.rangeUnderflow)).toBe(true);
    await page.getByLabel("Capacidad", { exact: true }).fill("20");
    await page.getByRole("button", { name: "Registrar aula", exact: true }).click();
    await expect(page.getByRole("alert").filter({ hasText: "Esta clave ya está registrada" })).toBeVisible();
  } finally { await page.request.delete(`/api/v1/classrooms/${id}`, { headers: mutations }); }
});

test("VIEWER consulta, no ve administración y recibe403 en cada mutación", async ({ page }) => {
  await login(page, "VIEWER");
  await capture(page, "07-aulas-viewer");
  await expect(page.getByRole("link", { name: "Nueva aula", exact: true })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /^Editar / })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /^Dar de baja / })).toHaveCount(0);
  const list = await page.request.get("/api/v1/classrooms");
  const { items } = await list.json();
  expect(items.length).toBeGreaterThan(0);
  const id = items[0].id;
  const input = { clave: "FORBIDDEN", nombre: "No permitida", edificio: "Pruebas", capacidad: 20, tipo: "TEORICA", estado: "ACTIVA" };
  expect((await page.request.post("/api/v1/classrooms", { headers: mutations, data: input })).status()).toBe(403);
  expect((await page.request.put(`/api/v1/classrooms/${id}`, { headers: mutations, data: input })).status()).toBe(403);
  expect((await page.request.patch(`/api/v1/classrooms/${id}`, { headers: mutations, data: { nombre: "No permitida" } })).status()).toBe(403);
  expect((await page.request.delete(`/api/v1/classrooms/${id}`, { headers: mutations })).status()).toBe(403);
  await page.goto(`/aulas/${id}`);
  await expect(page.getByRole("heading", { name: items[0].nombre, exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Editar aula", exact: true })).toHaveCount(0);
  await page.goto(`/aulas/${id}/editar`);
  await expect(page.getByRole("heading", { name: "Acceso de consulta", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Cerrar sesión", exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
  expect((await page.request.get("/api/v1/auth/me")).status()).toBe(401);
});

test("consulta móvil sin desbordamiento del documento", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page, "VIEWER");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await capture(page, "08-aulas-movil");
  await page.getByRole("button", { name: "Abrir menú", exact: true }).click();
  await expect(page.getByRole("navigation", { name: "Navegación principal" })).toBeVisible();
  await page.getByRole("button", { name: "Cerrar menú", exact: true }).last().click();
  await page.getByRole("button", { name: "Cerrar sesión", exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
});
