import { get } from './api.js';

// Fetch all users and build lookup maps keyed by id and discord_id.
export async function fetchUserMaps() {
  const data = await get('/api/users');
  const byId = new Map();
  const byDiscordId = new Map();

  for (const u of data.users) {
    const name = u.username || u.discord_id;
    byId.set(u.id, name);
    byDiscordId.set(u.discord_id, name);
  }

  return { byId, byDiscordId };
}
