/**
 * 白盒：禁止在 Vue/TS 中直接把 error.message 展示给用户（应走 getUserFacingErrorMessage）。
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC = path.join(__dirname, '..', 'src');

const ALLOW = new Set([
  'lib/user-facing-error.ts',
  'api/http.ts',
  'composables/useKnowledgeVectorNotice.ts',
  'composables/chat/chatSendErrors.ts'
]);

const PATTERN = /error instanceof (?:Error|ApiError)\s*\?\s*error\.message/;

function walk(dir, out = []) {
  for (const name of fs.readdirSync(dir)) {
    const full = path.join(dir, name);
    if (fs.statSync(full).isDirectory()) {
      if (name === 'node_modules') continue;
      walk(full, out);
    } else if (/\.(vue|ts)$/.test(name)) {
      out.push(full);
    }
  }
  return out;
}

const hits = [];
for (const file of walk(SRC)) {
  const rel = path.relative(SRC, file).split(path.sep).join('/');
  if (ALLOW.has(rel)) continue;
  const text = fs.readFileSync(file, 'utf8');
  if (PATTERN.test(text)) {
    hits.push(rel);
  }
}

if (hits.length) {
  console.error('Direct error.message UI pattern found (use getUserFacingErrorMessage):');
  for (const h of hits.sort()) console.error(`  - ${h}`);
  process.exit(1);
}

console.log('API error i18n guard OK.');
