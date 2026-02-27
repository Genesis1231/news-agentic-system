# Burst.fm Workers API

This folder contains Cloudflare Workers code for the burst.fm API endpoints.

## Setup

1. Install Wrangler globally if you haven't already:
   ```
   npm install -g wrangler
   ```

2. Authenticate with Cloudflare:
   ```
   wrangler login
   ```

3. Update the `wrangler.toml` file with your D1 database ID:
   ```toml
   [[d1_databases]]
   binding = "DB"
   database_name = "burstdb"
   database_id = "YOUR_DATABASE_ID" # Replace with your actual D1 database ID
   ```

4. Deploy the worker:
   ```
   wrangler deploy
   ```

## Development

For local development, you can use:
```
wrangler dev
```

## Database Setup

The worker will automatically create the necessary table schema when it first runs.

You can also manually set up the database schema:
```
wrangler d1 execute burstdb --command "CREATE TABLE IF NOT EXISTS subscribers (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL, created_at TEXT NOT NULL);"
```

## Endpoints

- `POST /api/subscribe` - Subscribe a new email address
  - Request body: `{ "email": "user@example.com" }`
  - Responses:
    - 201: Subscription successful
    - 200: Already subscribed
    - 400: Invalid email
    - 500: Server error
