const BASE = '';

// Send an HTTP request and return the response, throwing on non-OK status.
async function request(method: string, path: string, body?: unknown, options: RequestInit = {}): Promise<Response> {
  const url = `${BASE}${path}`;
  const headers: Record<string, string> = {};
  const init: RequestInit = { method, headers, ...options };

  if (body && !(body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(body);

  } else if (body instanceof FormData) {
    init.body = body;
  }

  const res = await fetch(url, init);

  if (!res.ok) {
    const text = await res.text();
    let message: string;

    try {
      const json = JSON.parse(text) as Record<string, unknown>;
      const errorObj = json.error as Record<string, unknown> | undefined;
      message = (json.detail as string) || (errorObj?.message as string) || text;
    } catch {
      message = text;
    }

    throw new Error(`${res.status}: ${message}`);
  }

  return res;
}

// Send a GET request and return the parsed JSON response.
export async function get(path: string): Promise<any> {
  const res = await request('GET', path);
  return res.json();
}

// Send a POST request with an optional JSON body and return the parsed response.
export async function post(path: string, body?: unknown): Promise<any> {
  const res = await request('POST', path, body);
  return res.json();
}

// Send a DELETE request and return the parsed JSON response.
export async function del(path: string): Promise<any> {
  const res = await request('DELETE', path);
  return res.json();
}

// Send a POST request with FormData and return the parsed JSON response.
export async function postForm(path: string, formData: FormData): Promise<any> {
  const res = await request('POST', path, formData);
  return res.json();
}

// Send a POST request and return the response as a Blob for audio playback.
export async function getAudio(path: string, body: unknown): Promise<Blob> {
  const res = await request('POST', path, body);
  return res.blob();
}

// Send a GET request and return the response as a Blob for binary downloads.
export async function getBlob(path: string): Promise<Blob> {
  const res = await request('GET', path);
  return res.blob();
}
