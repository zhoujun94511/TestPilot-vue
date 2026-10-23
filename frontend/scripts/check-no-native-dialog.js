/**
 * Fail if browser-native blocking dialogs are used in app source.
 * Prefer ConfirmDialog / in-app notices instead.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const SRC_DIR = path.join(ROOT, "src");

const PATTERNS = [
  { name: "window.confirm", re: /\bwindow\.confirm\s*\(/g },
  { name: "window.alert", re: /\bwindow\.alert\s*\(/g },
  { name: "window.prompt", re: /\bwindow\.prompt\s*\(/g },
  { name: "global confirm()", re: /(?:^|[^.\w])confirm\s*\(/g }
];

function walk(dir, acc) {
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, ent.name);
    if (ent.isDirectory()) {
      walk(p, acc);
    } else if (/\.(vue|[cm]?ts|tsx|jsx|js)$/.test(ent.name)) {
      acc.push(p);
    }
  }
}

const files = [];
walk(SRC_DIR, files);

let failed = false;
for (const file of files) {
  const text = fs.readFileSync(file, "utf8");
  for (const { name, re } of PATTERNS) {
    re.lastIndex = 0;
    if (!re.test(text)) continue;
    // Allow local function named `confirm` in ConfirmDialog (emit helper)
    if (name === "global confirm()" && file.replace(/\\/g, "/").endsWith("components/common/ConfirmDialog.vue")) {
      continue;
    }
    console.error(`[check-no-native-dialog] ${name} in ${path.relative(ROOT, file)}`);
    failed = true;
  }
}

if (failed) {
  console.error("\nUse @/components/common/ConfirmDialog.vue or existing banner/notice patterns.");
  process.exit(1);
}

console.log("check-no-native-dialog: OK");
