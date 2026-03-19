import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const app = express();
const PORT = process.env.PORT || 8000;

const RAW_HOST = process.env.DATABRICKS_HOST || '';
const DATABRICKS_HOST = RAW_HOST
  ? (RAW_HOST.startsWith('http') ? RAW_HOST : `https://${RAW_HOST}`)
  : null;

// M2M credentials — auto-injected by Databricks Apps runtime (never hardcoded)
const CLIENT_ID     = process.env.DATABRICKS_CLIENT_ID;
const CLIENT_SECRET = process.env.DATABRICKS_CLIENT_SECRET;

// Token cache for M2M flow
let cachedToken = null;
let tokenExpiresAt = 0;

async function fetchM2MToken() {
  if (!DATABRICKS_HOST || !CLIENT_ID || !CLIENT_SECRET) {
    throw new Error(
      `Missing M2M credentials — host: ${!!DATABRICKS_HOST}, client_id: ${!!CLIENT_ID}, client_secret: ${!!CLIENT_SECRET}`
    );
  }
  const url = `${DATABRICKS_HOST}/oidc/v1/token`;
  const body = new URLSearchParams({ grant_type: 'client_credentials', scope: 'all-apis' });
  const credentials = Buffer.from(`${CLIENT_ID}:${CLIENT_SECRET}`).toString('base64');

  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Authorization': `Basic ${credentials}`,
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: body.toString(),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`OAuth token fetch failed ${res.status}: ${text}`);
  }
  const json = await res.json();
  const expiresIn = (json.expires_in || 3600) - 300;
  cachedToken = json.access_token;
  tokenExpiresAt = Date.now() + expiresIn * 1000;
  return cachedToken;
}

async function getM2MToken() {
  if (cachedToken && Date.now() < tokenExpiresAt) return cachedToken;
  return fetchM2MToken();
}

// Auth priority:
//   1. x-forwarded-access-token  — user token injected by Databricks Apps proxy
//   2. DATABRICKS_CLIENT_ID/SECRET — app service principal auto-injected by Databricks Apps runtime
//   3. DATABRICKS_TOKEN           — local development fallback
async function resolveToken(req) {
  const forwarded = req.headers['x-forwarded-access-token'];
  if (forwarded) return { token: forwarded, method: 'x-forwarded-access-token' };

  const envToken = process.env.DATABRICKS_TOKEN;
  if (envToken) return { token: envToken, method: 'DATABRICKS_TOKEN' };

  if (CLIENT_ID && CLIENT_SECRET) {
    const token = await getM2MToken();
    return { token, method: 'client_credentials_m2m' };
  }

  throw new Error('No auth token available — x-forwarded-access-token not present, DATABRICKS_TOKEN not set, and no M2M credentials');
}

app.use(express.static(path.join(__dirname, 'frontend', 'dist')));
app.use(express.json());

async function databricksGet(apiPath, req) {
  if (!DATABRICKS_HOST) throw new Error('DATABRICKS_HOST not set');
  const { token } = await resolveToken(req);
  const res = await fetch(`${DATABRICKS_HOST}${apiPath}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Databricks API error ${res.status}: ${text}`);
  }
  return res.json();
}

// Health check
app.get('/api/health', async (req, res) => {
  let authMethod = 'none';
  try {
    const { method } = await resolveToken(req);
    authMethod = method;
  } catch (_) {}
  res.json({
    status: 'healthy',
    app: 'data-catalog-explorer',
    version: '2.3.1',
    databricks_host_configured: !!DATABRICKS_HOST,
    auth_method: authMethod,
  });
});

app.get('/api/catalogs', async (req, res) => {
  try {
    const data = await databricksGet('/api/2.1/unity-catalog/catalogs', req);
    res.json(data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/schemas', async (req, res) => {
  const { catalog_name } = req.query;
  if (!catalog_name) return res.status(400).json({ error: 'catalog_name required' });
  try {
    const data = await databricksGet(
      `/api/2.1/unity-catalog/schemas?catalog_name=${encodeURIComponent(catalog_name)}`,
      req
    );
    res.json(data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/tables', async (req, res) => {
  const { catalog_name, schema_name } = req.query;
  if (!catalog_name || !schema_name)
    return res.status(400).json({ error: 'catalog_name and schema_name required' });
  try {
    const data = await databricksGet(
      `/api/2.1/unity-catalog/tables?catalog_name=${encodeURIComponent(catalog_name)}&schema_name=${encodeURIComponent(schema_name)}`,
      req
    );
    res.json(data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/tables/:full_name', async (req, res) => {
  const { full_name } = req.params;
  try {
    const data = await databricksGet(
      `/api/2.1/unity-catalog/tables/${encodeURIComponent(full_name)}`,
      req
    );
    res.json(data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('*', (_req, res) => {
  res.sendFile(path.join(__dirname, 'frontend', 'dist', 'index.html'));
});

app.listen(PORT, () => {
  console.log(`Data Catalog Explorer v2.3.1 running on port ${PORT}`);
  console.log(`Host: ${DATABRICKS_HOST || '(not set)'} | M2M available: ${!!(CLIENT_ID && CLIENT_SECRET)}`);
});
