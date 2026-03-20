import { TelegramMessage } from '../types';

const CACHE_VERSION = 1;
const CACHE_KEY_PREFIX = 'tggod_msg_cache_';
const MAX_MESSAGES_PER_GROUP = 100;
const CACHE_TTL_MS = 30 * 60 * 1000; // 30 minutes
const MAX_GROUPS_CACHED = 10;

interface MessageCacheEntry {
  version: number;
  groupId: number;
  messages: TelegramMessage[];
  cachedAt: number;
}

function getCacheKey(groupId: number): string {
  return `${CACHE_KEY_PREFIX}${groupId}`;
}

function getGroupIndexKey(): string {
  return `${CACHE_KEY_PREFIX}index`;
}

export const messageCacheService = {
  saveMessages(groupId: number, messages: TelegramMessage[]): void {
    try {
      const entry: MessageCacheEntry = {
        version: CACHE_VERSION,
        groupId,
        messages: messages.slice(0, MAX_MESSAGES_PER_GROUP),
        cachedAt: Date.now(),
      };
      localStorage.setItem(getCacheKey(groupId), JSON.stringify(entry));

      const indexRaw = localStorage.getItem(getGroupIndexKey());
      const index: number[] = indexRaw ? JSON.parse(indexRaw) : [];
      const updated = [groupId, ...index.filter((id) => id !== groupId)].slice(0, MAX_GROUPS_CACHED);

      if (updated.length < index.length) {
        const evicted = index.slice(MAX_GROUPS_CACHED);
        evicted.forEach((id) => localStorage.removeItem(getCacheKey(id)));
      }

      localStorage.setItem(getGroupIndexKey(), JSON.stringify(updated));
    } catch {
      // localStorage may be full — silently skip caching
    }
  },

  getMessages(groupId: number): TelegramMessage[] | null {
    try {
      const raw = localStorage.getItem(getCacheKey(groupId));
      if (!raw) return null;

      const entry: MessageCacheEntry = JSON.parse(raw);
      if (entry.version !== CACHE_VERSION) {
        localStorage.removeItem(getCacheKey(groupId));
        return null;
      }

      if (Date.now() - entry.cachedAt > CACHE_TTL_MS) {
        localStorage.removeItem(getCacheKey(groupId));
        return null;
      }

      return entry.messages;
    } catch {
      return null;
    }
  },

  invalidate(groupId: number): void {
    localStorage.removeItem(getCacheKey(groupId));
  },

  clearAll(): void {
    const indexRaw = localStorage.getItem(getGroupIndexKey());
    const index: number[] = indexRaw ? JSON.parse(indexRaw) : [];
    index.forEach((id) => localStorage.removeItem(getCacheKey(id)));
    localStorage.removeItem(getGroupIndexKey());
  },
};
