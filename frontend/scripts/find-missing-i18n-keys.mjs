/**
 * Fail if t('...') keys used in src are missing from reference locale messages.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const SRC_DIR = path.join(ROOT, "src");
const REF_DIR = path.join(SRC_DIR, "i18n", "en");
const MESSAGE_NAMESPACE_BY_FILE = {
  "config-center.ts": "configCenter",
  "experimental-tools-page.ts": "experimentalToolsPage"
};
const DYNAMIC_PREFIXES = [
  "configCenter.itemLabel.",
  "configCenter.itemDescription.",
  "configCenter.category.",
  "configCenter.categoryDescription.",
  "configCenter.provider.",
  "configCenter.providerUi.",
  "enums.",
  "ai."
];

function messageNamespaceForFile(fileName) {
  return MESSAGE_NAMESPACE_BY_FILE[fileName] || fileName.replace(/\.ts$/, "");
}

function loadTsDefaultObject(filePath) {
  const raw = fs.readFileSync(filePath, "utf8");
  const normalized = raw.replace(/^\uFEFF/, "").trim();
  const exportDefaultMatch = normalized.match(/export\s+default\s+([\s\S]*?);?\s*$/);
  if (!exportDefaultMatch) throw new Error(`Cannot parse: ${filePath}`);
  const loader = new Function(`return (${exportDefaultMatch[1]});`);
  return loader();
}

function collectKeys(obj, prefix = "") {
  const output = new Map();
  if (obj === null || typeof obj !== "object" || Array.isArray(obj)) return output;
  for (const key of Object.keys(obj)) {
    const nextPath = prefix ? `${prefix}.${key}` : key;
    const val = obj[key];
    if (val && typeof val === "object" && !Array.isArray(val)) {
      for (const [k, t] of collectKeys(val, nextPath)) output.set(k, t);
    } else {
      output.set(nextPath, typeof val);
    }
  }
  return output;
}

function listSourceFiles(dir, acc = []) {
  for (const name of fs.readdirSync(dir)) {
    const full = path.join(dir, name);
    const stat = fs.statSync(full);
    if (stat.isDirectory()) {
      if (name !== "i18n" && name !== "node_modules") listSourceFiles(full, acc);
      continue;
    }
    if ((name.endsWith(".ts") || name.endsWith(".vue")) && !name.endsWith(".d.ts")) {
      acc.push(full);
    }
  }
  return acc;
}

const messages = new Set();
for (const file of fs.readdirSync(REF_DIR).filter((f) => f.endsWith(".ts") && f !== "index.ts")) {
  const ns = messageNamespaceForFile(file);
  const obj = loadTsDefaultObject(path.join(REF_DIR, file));
  for (const [keyPath] of collectKeys(obj)) {
    messages.add(`${ns}.${keyPath}`);
  }
}

const used = new Set();
const re = /\bt\(\s*['"]([^'"]+)['"]/g;
for (const file of listSourceFiles(SRC_DIR)) {
  const content = fs.readFileSync(file, "utf8");
  let m;
  while ((m = re.exec(content))) used.add(m[1]);
}

function isDynamic(key) {
  return DYNAMIC_PREFIXES.some((p) => key.startsWith(p));
}

const missing = [...used].filter((k) => !messages.has(k) && !isDynamic(k)).sort();

if (missing.length) {
  console.error(`Missing i18n keys (${missing.length}):`);
  missing.forEach((k) => console.error(`  ${k}`));
  process.exit(1);
}
console.log(`OK: ${used.size} t() keys resolved in en messages.`);
