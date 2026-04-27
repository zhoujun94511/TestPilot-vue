import { createI18n } from 'vue-i18n';
import zhCommon from './zh-CN/common';
import zhDashboard from './zh-CN/dashboard';
import zhChat from './zh-CN/chat';
import zhConfig from './zh-CN/config';
import zhCases from './zh-CN/cases';
import zhDocuments from './zh-CN/documents';
import zhKnowledge from './zh-CN/knowledge';
import zhAi from './zh-CN/ai';
import zhValidation from './zh-CN/validation';
import zhEnums from './zh-CN/enums';
import zhConfigCenter from './zh-CN/config-center';
import enCommon from './en/common';
import enDashboard from './en/dashboard';
import enChat from './en/chat';
import enConfig from './en/config';
import enCases from './en/cases';
import enDocuments from './en/documents';
import enKnowledge from './en/knowledge';
import enAi from './en/ai';
import enValidation from './en/validation';
import enEnums from './en/enums';
import enConfigCenter from './en/config-center';

export type Locale = 'zh-CN' | 'en';
export const LOCALE_STORAGE_KEY = 'testpilot_locale';

function detectLocale(): Locale {
  const saved = localStorage.getItem(LOCALE_STORAGE_KEY);
  if (saved === 'zh-CN' || saved === 'en') {
    return saved;
  }

  const browserLocale = navigator.language?.toLowerCase() || 'zh-cn';
  return browserLocale.startsWith('zh') ? 'zh-CN' : 'en';
}

const messages = {
  'zh-CN': {
    common: zhCommon,
    dashboard: zhDashboard,
    chat: zhChat,
    config: zhConfig,
    cases: zhCases,
    documents: zhDocuments,
    knowledge: zhKnowledge,
    ai: zhAi,
    validation: zhValidation,
    enums: zhEnums,
    configCenter: zhConfigCenter
  },
  en: {
    common: enCommon,
    dashboard: enDashboard,
    chat: enChat,
    config: enConfig,
    cases: enCases,
    documents: enDocuments,
    knowledge: enKnowledge,
    ai: enAi,
    validation: enValidation,
    enums: enEnums,
    configCenter: enConfigCenter
  }
};

const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale: detectLocale(),
  fallbackLocale: 'zh-CN',
  messages
});

export function setLocale(locale: Locale) {
  i18n.global.locale.value = locale;
  localStorage.setItem(LOCALE_STORAGE_KEY, locale);
}

export default i18n;
