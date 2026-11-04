/**
 * White-box check: every var(--tp-*) referenced in src (vue/ts/css under frontend)
 * must be defined in src/styles/tokens.css (:root or [data-theme="dark"]).
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FRONTEND = path.resolve(__dirname, "..");
const TOKENS_FILE = path.join(FRONTEND, "src", "styles", "tokens.css");
const SCAN_ROOT = path.join(FRONTEND, "src");

const IGNORE_VAR_PREFIXES = [];

function walk(dir, out = []) {
  for (const name of fs.readdirSync(dir)) {
    const full = path.join(dir, name);
    const stat = fs.statSync(full);
    if (stat.isDirectory()) {
      if (name === "node_modules") continue;
      walk(full, out);
    } else if (/\.(vue|ts|css)$/.test(name)) {
      out.push(full);
    }
  }
  return out;
}

function loadDefinedTokens(css) {
  const defined = new Set();
  for (const m of css.matchAll(/^\s*(--tp-[a-z0-9-]+)\s*:/gm)) {
    defined.add(m[1]);
  }
  return defined;
}

function collectReferences(text) {
  const refs = new Set();
  for (const m of text.matchAll(/var\(\s*(--tp-[a-z0-9-]+)/g)) {
    refs.add(m[1]);
  }
  return refs;
}

const tokensCss = fs.readFileSync(TOKENS_FILE, "utf8");
const defined = loadDefinedTokens(tokensCss);
const allRefs = new Set();

for (const file of walk(SCAN_ROOT)) {
  const text = fs.readFileSync(file, "utf8");
  for (const ref of collectReferences(text)) {
    allRefs.add(ref);
  }
}

const missing = [...allRefs].filter((name) => {
  if (IGNORE_VAR_PREFIXES.some((p) => name.startsWith(p))) return false;
  return !defined.has(name);
}).sort();

if (missing.length) {
  console.error("Undefined --tp-* token references (not in tokens.css):");
  for (const name of missing) {
    console.error(`  - ${name}`);
  }
  process.exit(1);
}

console.log(`Theme token check OK (${defined.size} defined, ${allRefs.size} referenced).`);
