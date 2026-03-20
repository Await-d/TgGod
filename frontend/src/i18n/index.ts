import { useCallback } from 'react';
import { useUserSettingsStore } from '../store/userSettingsStore';

import zhMessages from './locales/zh.json';
import enMessages from './locales/en.json';

type Messages = typeof zhMessages;

const locales: Record<string, Messages> = {
  zh_CN: zhMessages,
  en_US: enMessages,
};

function getNestedValue(obj: any, path: string): string {
  return path.split('.').reduce((acc, key) => acc?.[key], obj) ?? path;
}

export function useTranslation() {
  const language = useUserSettingsStore((s) => s.settings.language);
  const messages = locales[language] ?? locales['zh_CN'];

  const t = useCallback(
    (key: string, vars?: Record<string, string>) => {
      let str = getNestedValue(messages, key);
      if (vars) {
        Object.entries(vars).forEach(([k, v]) => {
          str = str.replace(`{${k}}`, v);
        });
      }
      return str;
    },
    [messages]
  );

  return { t, language };
}
