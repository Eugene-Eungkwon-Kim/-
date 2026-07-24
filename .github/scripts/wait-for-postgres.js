#!/usr/bin/env node

const pg = require('pg');

const config = {
  host: process.env.PG_HOST || 'postgres',
  port: parseInt(process.env.PG_PORT || '5432'),
  user: process.env.PG_USER || 'postgres',
  password: process.env.PG_PASSWORD || 'postgres',
  database: 'postgres',
  connectionTimeoutMillis: 2000,
};

let attempts = 0;
const maxAttempts = 60;

async function connect() {
  try {
    const client = await new pg.Client(config).connect();
    console.log('✓ PostgreSQL connected');
    client.end();
    process.exit(0);
  } catch (err) {
    attempts++;
    if (attempts >= maxAttempts) {
      console.error('✗ PostgreSQL connection failed');
      process.exit(1);
    }
    console.log(`Attempt ${attempts}/${maxAttempts}...`);
    setTimeout(connect, 500);
  }
}

connect();
