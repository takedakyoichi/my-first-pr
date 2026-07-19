const EMPTY = { pages: {}, activityDates: [] };

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

export function userKey(request) {
  return request.headers.get("Cf-Access-Authenticated-User-Email") || "default";
}

export async function onRequestGet(context) {
  const key = userKey(context.request);
  const raw = await context.env.STATE_KV.get(key);
  if (!raw) return json(EMPTY);
  try {
    return json(JSON.parse(raw));
  } catch {
    return json(EMPTY);
  }
}

export async function onRequestPut(context) {
  const key = userKey(context.request);
  const body = await context.request.json();
  const state = {
    pages: body.pages ?? {},
    activityDates: body.activityDates ?? [],
  };
  await context.env.STATE_KV.put(key, JSON.stringify(state));
  return json({ ok: true });
}
