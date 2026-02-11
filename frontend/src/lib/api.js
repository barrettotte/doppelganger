const BASE = '';

// Send an HTTP request and return the response, throwing on non-OK status.
async function request(method, path, body, options = {}) {
  const url = `${BASE}${path}`;
  const headers = {};
  const init = { method, headers, ...options };

  if (body && !(body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(body);

  } else if (body instanceof FormData) {
    init.body = body;
  }

  const res = await fetch(url, init);

  if (!res.ok) {
    const text = await res.text();
    let message;
  
    try {
      const json = JSON.parse(text);
      message = json.detail || json.error?.message || text;
    } catch {
      message = text;
    }

    throw new Error(`${res.status}: ${message}`);
  }

  return res;
}

// Send a GET request and return the parsed JSON response.
export async function get(path) {
  const res = await request('GET', path);
  return res.json();
}

// Send a POST request with an optional JSON body and return the parsed response.
export async function post(path, body = null) {
  const res = await request('POST', path, body);
  return res.json();
}

// Send a DELETE request and return the parsed JSON response.
export async function del(path) {
  const res = await request('DELETE', path);
  return res.json();
}

// Send a POST request with FormData and return the parsed JSON response.
export async function postForm(path, formData) {
  const res = await request('POST', path, formData);
  return res.json();
}

// Send a POST request and return the response as a Blob for audio playback.
export async function getAudio(path, body) {
  const res = await request('POST', path, body);
  return res.blob();
}

// Send a GET request and return the response as a Blob for binary downloads.
export async function getBlob(path) {
  const res = await request('GET', path);
  return res.blob();
}
