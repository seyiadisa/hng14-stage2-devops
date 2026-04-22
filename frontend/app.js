const express = require('express');
const axios = require('axios');
const path = require('path');
const app = express();

const API_URL = process.env.API_URL || 'http://localhost:8000';
const PORT = Number(process.env.PORT || 3000);
const HOST = process.env.HOST || '0.0.0.0';

const client = axios.create({
  baseURL: API_URL,
  timeout: 5000,
});

app.use(express.json());
app.use(express.static(path.join(__dirname, 'views')));

app.get('/health', (_req, res) => {
  res.json({ status: 'ok' });
});

app.post('/submit', async (_req, res) => {
  try {
    const response = await client.post(`/jobs`);
    res.json(response.data);
  } catch (err) {
    const status = err.response?.status || 502;
    const detail = err.response?.data || { error: 'API unavailable' };
    res.status(status).json(detail);
  }
});

app.get('/status/:id', async (req, res) => {
  try {
    const response = await client.get(`/jobs/${req.params.id}`);
    res.json(response.data);
  } catch (err) {
    const status = err.response?.status || 502;
    const detail = err.response?.data || { error: 'API unavailable' };
    res.status(status).json(detail);
  }
});

app.listen(PORT, HOST, () => {
  console.log(`Frontend running on http://${HOST}:${PORT}`);
});
