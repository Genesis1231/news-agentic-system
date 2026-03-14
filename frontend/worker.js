const R2_PUBLIC = 'https://pub-c163d15064354af0a8ac3b349f32512d.r2.dev';

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Proxy /audio/* to R2 — same origin eliminates CORS for Web Audio API
    if (url.pathname.startsWith('/audio/')) {
      if (request.method === 'OPTIONS') {
        return new Response(null, {
          headers: {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
          },
        });
      }

      const r2Response = await fetch(`${R2_PUBLIC}${url.pathname}`);
      if (!r2Response.ok) {
        return new Response('Not found', { status: 404 });
      }

      const headers = new Headers(r2Response.headers);
      headers.set('Access-Control-Allow-Origin', '*');
      headers.set('Access-Control-Allow-Methods', 'GET, HEAD, OPTIONS');
      headers.set('Cache-Control', 'public, max-age=86400');

      return new Response(r2Response.body, {
        status: r2Response.status,
        headers,
      });
    }

    // Everything else → static assets (SPA fallback handled by wrangler config)
    return env.ASSETS.fetch(request);
  },
};
