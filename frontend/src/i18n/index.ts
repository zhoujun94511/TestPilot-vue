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
import zhAuth from './zh-CN/auth';
import zhAdmin from './zh-CN/admin';
import zhExperimentalToolsPage from './zh-CN/experimental-tools-page';
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
import enAuth from './en/auth';
import enAdmin from './en/admin';
import enExperimentalToolsPage from './en/experimental-tools-page';

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
    configCenter: zhConfigCenter,
    auth: zhAuth,
    admin: zhAdmin,
    experimentalToolsPage: zhExperimentalToolsPage
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
    configCenter: enConfigCenter,
    auth: enAuth,
    admin: enAdmin,
    experimentalToolsPage: enExperimentalToolsPage
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
