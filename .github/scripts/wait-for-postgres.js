#!/usr/bin/env node

console.log('Starting PostgreSQL connection test...');

try {
  const pg = require('pg');
  console.log('✓ pg module loaded');
} catch (err) {
  console.error('✗ Failed to load pg module:', err.message);
  process.exit(1);
}

const pg = require('pg');

const config = {
  host: process.env.PG_HOST || 'postgres',
  port: parseInt(process.env.PG_PORT || '5432'),
  user: process.env.PG_USER || 'postgres',
  password: process.env.PG_PASSWORD || 'postgres',
  database: 'postgres',
  connectionTimeoutMillis: 5000,
};

console.log(`Connecting to PostgreSQL at ${config.host}:${config.port} as ${config.user}`);

let attempts = 0;
const maxAttempts = 30;

async function connect() {
  try {
    console.log(`[${attempts + 1}/${maxAttempts}] Creating connection pool...`);
    const adminPool = new pg.Pool(config);

    console.log(`[${attempts + 1}/${maxAttempts}] Attempting to connect...`);
    const adminClient = await adminPool.connect();
    console.log('✓ PostgreSQL connection successful');

    // Verify connection with simple query
    const result = await adminClient.query('SELECT version()');
    console.log('✓ PostgreSQL version:', result.rows[0].version.split(',')[0]);

    // Create test database if it doesn't exist
    try {
      console.log('Creating database maars_test...');
      await adminClient.query('CREATE DATABASE maars_test');
      console.log('✓ Database maars_test created');
    } catch (err) {
      if (err.code === '42P04') {
        console.log('✓ Database maars_test already exists');
      } else {
        throw err;
      }
    }

    adminClient.release();
    await adminPool.end();
    console.log('✓ PostgreSQL ready - all systems go');
    process.exit(0);
  } catch (err) {
    attempts++;
    if (attempts >= maxAttempts) {
      console.error(`✗ PostgreSQL initialization failed after ${maxAttempts} attempts`);
      console.error('Final error:', err.message);
      console.error('Error code:', err.code);
      console.error('Error stack:', err.stack);
      process.exit(1);
    }
    console.log(`[${attempts}/${maxAttempts}] Connection failed (${err.code || 'unknown'}): ${err.message}`);
    setTimeout(connect, 1000);
  }
}

connect();
