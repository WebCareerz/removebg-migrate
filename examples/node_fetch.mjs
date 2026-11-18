// Node.js 18 or later (built-in fetch, FormData and Blob)
import { readFile, writeFile } from 'node:fs/promises';

// const API_BASE = 'https://api.remove.bg';                       // before
const API_BASE = process.env.BG_API_BASE ?? 'https://api.clearbg.org'; // after

const form = new FormData();
form.append('image_file', new Blob([await readFile('photo.jpg')]), 'photo.jpg');
form.append('size', 'full');

async function post(attempt = 0) {
  const res = await fetch(`${API_BASE}/v1.0/removebg`, {
    method: 'POST',
    headers: { 'X-Api-Key': process.env.BG_API_KEY },
    body: form,
    signal: AbortSignal.timeout(150_000),
  });
  // 429: over 500 requests/minute per key, or more than 4 images in flight per account.
  if ((res.status === 429 || res.status === 503) && attempt < 4) {
    const wait = Number(res.headers.get('Retry-After') ?? 2);
    await new Promise((r) => setTimeout(r, wait * 1000));
    return post(attempt + 1);
  }
  return res;
}

const res = await post();
if (!res.ok) throw new Error(JSON.stringify(await res.json()));
await writeFile('photo-no-bg.png', Buffer.from(await res.arrayBuffer()));
console.log('credits charged:', res.headers.get('X-Credits-Charged'));
