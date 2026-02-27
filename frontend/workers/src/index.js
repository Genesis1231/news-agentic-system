// Worker script for handling email subscriptions with D1

export default {
  async fetch(request, env, ctx) {
    // Enable CORS
    if (request.method === 'OPTIONS') {
      return handleCORS();
    }

    // Route requests
    const url = new URL(request.url);
    if (url.pathname === '/api/subscribe' && request.method === 'POST') {
      return handleSubscribe(request, env);
    }

    return new Response('Not found', { status: 404 });
  },
};

// Handle the email subscription
async function handleSubscribe(request, env) {
  try {
    // Parse the request body
    const data = await request.json();
    const { email } = data;

    if (!email) {
      return jsonResponse({ error: 'Email is required' }, 400);
    }

    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return jsonResponse({ error: 'Invalid email format' }, 400);
    }

    // Check if the subscribers table exists, create if not
    try {
      await env.DB.prepare(`
        CREATE TABLE IF NOT EXISTS subscribers (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          email TEXT UNIQUE NOT NULL,
          created_at TEXT NOT NULL
        )
      `).run();
    } catch (error) {
      console.error('Table creation error:', error);
      return jsonResponse({ error: 'Database initialization failed' }, 500);
    }

    // Check if the email already exists
    const existingEmail = await env.DB.prepare(`
      SELECT email FROM subscribers WHERE email = ?
    `).bind(email).first();

    if (existingEmail) {
      return jsonResponse({ 
        message: 'You are already subscribed!',
        status: 'existing' 
      }, 200);
    }

    // Insert the new subscriber
    const timestamp = new Date().toISOString();
    await env.DB.prepare(`
      INSERT INTO subscribers (email, created_at) VALUES (?, ?)
    `).bind(email, timestamp).run();

    return jsonResponse({ 
      message: 'Subscription successful!',
      status: 'success' 
    }, 201);
  } catch (error) {
    console.error('Subscription error:', error);
    return jsonResponse({ error: 'Failed to process subscription' }, 500);
  }
}

// Helper function for CORS
function handleCORS() {
  return new Response(null, {
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
      'Access-Control-Max-Age': '86400',
    },
  });
}

// Helper function for JSON responses
function jsonResponse(data, status = 200) {
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Content-Type': 'application/json',
  };
  
  return new Response(JSON.stringify(data), { 
    status,
    headers 
  });
}
