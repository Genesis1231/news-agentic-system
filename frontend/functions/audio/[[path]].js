const R2_PUBLIC = 'https://pub-c163d15064354af0a8ac3b349f32512d.r2.dev';

export async function onRequest(context) {
  const path = context.params.path.join('/');
  const r2Url = `${R2_PUBLIC}/audio/${path}`;

  const r2Response = await fetch(r2Url);
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
