const MISTRAL_API_BASE = 'https://api.mistral.ai/v1';

const AGENT_INSTRUCTIONS = `Ты — Тля, глава Архива домика. Пользователь — игрок. Обращайся к нему как к игроку, уважительно и по-доброму, но не называй его помощником. Отвечай только на русском языке, кроме названия игры Grounded 2 и общепринятых игровых терминов.

В каждом запросе тебе передаётся полный индекс каталога Архива дворика и подробные записи, найденные на сайте. Сначала используй данные каталога. Если ответа там нет, нужна актуальная информация или нужна проверка внешнего источника, используй встроенный инструмент web_search. Не выдумывай координаты, рецепты или характеристики. Источники из интернета указывай в конце ответа.

У тебя есть доступ к визуальным карточкам сайта. Если упоминаешь предмет из контекста, добавляй маркер [ITEM id="точный-id"]. Для набора предметов используй [SET title="русское название набора" ids="id1,id2,id3"]. Для ссылки используй [LINK url="https://..." title="русское название"]. Для изображения из разрешённого источника используй [IMAGE url="https://..." alt="русское описание"]. Используй только id, URL и изображения из контекста сайта или web_search. Не изменяй текст маркеров.`;

function corsHeaders(request, env) {
  const origin = request.headers.get('Origin') || '';
  const allowed = String(env.ALLOWED_ORIGIN || '*').split(',').map(value => value.trim()).filter(Boolean);
  const originAllowed = allowed.includes('*') || allowed.includes(origin);
  return {
    'Access-Control-Allow-Origin': originAllowed ? (allowed.includes('*') ? '*' : origin) : 'null',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '86400',
    'Vary': 'Origin',
    'Content-Type': 'application/json; charset=utf-8'
  };
}

function jsonResponse(payload, request, env, status = 200) {
  return new Response(JSON.stringify(payload), { status, headers: corsHeaders(request, env) });
}

async function mistralRequest(path, env, body) {
  const response = await fetch(`${MISTRAL_API_BASE}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${env.MISTRAL_API_KEY}`
    },
    body: JSON.stringify(body)
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    return { ok: false, status: response.status, payload };
  }
  return { ok: true, status: response.status, payload };
}

export default {
  async fetch(request, env) {
    const headers = corsHeaders(request, env);
    const origin = request.headers.get('Origin') || '';
    const allowed = String(env.ALLOWED_ORIGIN || '*').split(',').map(value => value.trim()).filter(Boolean);
    if (!allowed.includes('*') && !allowed.includes(origin)) {
      return new Response(JSON.stringify({ error: 'Origin не разрешён.' }), { status: 403, headers });
    }
    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers });
    if (request.method !== 'POST' || new URL(request.url).pathname !== '/chat') {
      return jsonResponse({ error: 'Используй POST /chat.' }, request, env, 405);
    }
    if (!env.MISTRAL_API_KEY || !env.MISTRAL_AGENT_ID) {
      return jsonResponse({ error: 'В Worker не настроены MISTRAL_API_KEY и MISTRAL_AGENT_ID.' }, request, env, 500);
    }

    let body;
    try { body = await request.json(); } catch { return jsonResponse({ error: 'Некорректный JSON.' }, request, env, 400); }
    const question = String(body?.question || '').trim();
    const context = String(body?.context || '').trim();
    const conversationId = String(body?.conversationId || '').trim();
    if (!question) return jsonResponse({ error: 'Вопрос не может быть пустым.' }, request, env, 400);
    if (question.length > 2000) return jsonResponse({ error: 'Вопрос слишком длинный.' }, request, env, 413);
    if (context.length > 220000) return jsonResponse({ error: 'Контекст каталога слишком большой.' }, request, env, 413);

    const input = `${AGENT_INSTRUCTIONS}\n\n${context}\n\nВопрос игрока:\n${question}`;
    const path = conversationId ? `/conversations/${encodeURIComponent(conversationId)}` : '/conversations';
    const requestBody = conversationId ? { inputs: input } : { agent_id: env.MISTRAL_AGENT_ID, inputs: input };
    let result = await mistralRequest(path, env, requestBody);

    if (!result.ok && conversationId && [400, 404].includes(result.status)) {
      result = await mistralRequest('/conversations', env, { agent_id: env.MISTRAL_AGENT_ID, inputs: input });
    }
    if (!result.ok) {
      return jsonResponse({ error: result.payload?.message || result.payload?.detail || `Mistral вернул ошибку ${result.status}.` }, request, env, result.status);
    }

    const payload = result.payload || {};
    return jsonResponse({
      conversation_id: payload.conversation_id || payload.id || '',
      outputs: payload.outputs || [],
      choices: payload.choices || []
    }, request, env);
  }
};
