import { get } from './api';

// Fetch all users and build lookup maps keyed by id and discord_id.
export async function fetchUserMaps(): Promise<{ byId: Map<number, string>; byDiscordId: Map<string, string> }> {
  const data = await get('/api/users');
  const byId = new Map<number, string>();
  const byDiscordId = new Map<string, string>();

  for (const u of data.users) {
    const name = u.username || u.discord_id;
    byId.set(u.id, name);
    byDiscordId.set(u.discord_id, name);
  }

  return { byId, byDiscordId };
}
