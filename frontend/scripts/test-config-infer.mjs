/**
 * White-box: MAX_TOKENS / TR_* 必须为 number，API_KEY 仍为 password（与 inferInputKind 规则对齐）。
 */
import assert from 'node:assert/strict';

function isNumericTokenLimitKey(key) {
  const normalized = key.toUpperCase();
  if (normalized === 'MAX_TOKENS') return true;
  if (normalized === 'TOKEN_MAX_PER_SESSION' || normalized === 'TOKEN_MAX_CALLS_PER_SESSION') {
    return true;
  }
  return /^TR_[A-Z0-9]+_MAX_TOKENS$/.test(normalized);
}

function isSecretConfigField(key, description) {
  const upperKey = key.toUpperCase();
  if (/(?:^|_)API_KEY$|SECRET|PASSWORD|PRIVATE_KEY/.test(upperKey)) return true;
  if (/\bapi\s*key\b|api密钥|密钥|secret|password/i.test(description)) return true;
  return false;
}

function inferInputKind(raw) {
  const key = String(raw.key || '');
  const description = String(raw.description || '').toLowerCase();
  const valueType = String(raw.value_type || '').toLowerCase();

  if (['bool', 'boolean', 'switch'].includes(valueType)) return 'boolean';
  if (isNumericTokenLimitKey(key) || ['int', 'integer', 'float', 'number', 'decimal'].includes(valueType)) {
    return 'number';
  }
  if (raw.is_sensitive === true || isSecretConfigField(key, description)) return 'password';
  return 'string';
}

const samples = [
  ['MAX_TOKENS', 'number'],
  ['TR_OPENAI_MAX_TOKENS', 'number'],
  ['TOKEN_MAX_PER_SESSION', 'number'],
  ['OPENAI_API_KEY', 'password']
];

for (const [configKey, expected] of samples) {
  const kind = inferInputKind({
    key: configKey,
    value_type: configKey === 'OPENAI_API_KEY' ? 'string' : 'int',
    description: configKey.includes('API') ? 'OpenAI API密钥' : 'OpenAI 用例生成最大 Token 数',
    is_sensitive: configKey === 'OPENAI_API_KEY'
  });
  assert.equal(kind, expected, configKey);
}

console.log('test-config-infer: ok');
