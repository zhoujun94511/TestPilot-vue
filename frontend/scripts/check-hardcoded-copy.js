/**
 * Scan Vue SFC files for possibly hardcoded user-facing copy.
 *
 * Heuristics:
 * - text content between tags in <template>
 * - string literals in <script> containing CJK characters
 * - ignores common technical tokens / class names / URLs
 *
 * This script is best-effort and may report false positives.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const SRC_DIR = path.join(ROOT, "src");
const TARGET_DIRS = ["views", "components"];

function isUiPrimitiveFile(filePath) {
  const normalized = filePath.replaceAll("\\", "/");
  return normalized.includes("/components/ui/");
}

function isLikelyTailwindClassLiteral(text) {
  if (/\b(inline-flex|hover:|focus-visible:|text-foreground|text-muted|bg-primary|bg-secondary|bg-destructive|bg-accent|border-border|border-input|rounded-full|underline-offset)\b/.test(text)) {
    return true;
  }
  if (/\b(px-|py-|text-xs|text-sm|text-base|font-semibold|font-bold)\b/.test(text) && /\b(bg-|text-|border-|\[var\(--tp-)/.test(text)) {
    return true;
  }
  return false;
}

const IGNORE_LITERALS = new Set([
  "primary",
  "secondary",
  "danger",
  "warning",
  "success",
  "info",
  "ghost",
  "sm",
  "md",
  "lg",
  "text",
  "chat",
  "user",
  "assistant",
  "system",
  "api",
  "http",
  "https",
  "id",
  "key",
  "title",
  "label",
  "name",
  "value",
  "description",
  "placeholder",
  "type",
  "status",
  "loading",
  "error",
  "warning",
  "default",
  "index",
]);

function listVueFiles(dir, out = []) {
  if (!fs.existsSync(dir)) return out;
  for (const entry of fs.readdirSync(dir)) {
    const full = path.join(dir, entry);
    const stat = fs.statSync(full);
    if (stat.isDirectory()) {
      listVueFiles(full, out);
    } else if (entry.endsWith(".vue")) {
      out.push(full);
    }
  }
  return out;
}

function splitLines(content) {
  return content.split(/\r?\n/);
}

function likelyUserCopy(text) {
  const trimmed = text.trim();
  if (!trimmed) return false;
  if (trimmed.length <= 3) return false;
  if (/^[\d\s\-_:,./()[\]{}]+$/.test(trimmed)) return false;
  if (trimmed.includes("{{") || trimmed.includes("}}")) return false;
  if (trimmed.startsWith(":") || trimmed.startsWith("@")) return false;
  if (/^(class|style|key|ref|slot|name)=/.test(trimmed)) return false;
  if (/^https?:\/\//i.test(trimmed)) return false;
  if (/^[a-z0-9_.:/-]+$/i.test(trimmed)) return false;
  if (/^[A-Za-z0-9_.-]+$/.test(trimmed) && IGNORE_LITERALS.has(trimmed.toLowerCase())) return false;
  return /[\u4e00-\u9fff]/.test(trimmed) || /[A-Za-z]{3,}\s+[A-Za-z]{2,}/.test(trimmed);
}

function scanTemplate(lines, filePath) {
  const findings = [];
  let inTemplate = false;
  lines.forEach((line, idx) => {
    if (line.includes("<template")) inTemplate = true;
    if (line.includes("</template>")) inTemplate = false;
    if (!inTemplate) return;

    // rough text node capture
    const matches = line.matchAll(/>([^<>{}][^<]*)</g);
    for (const match of matches) {
      const text = match[1]?.trim() || "";
      if (!likelyUserCopy(text)) continue;
      findings.push({
        filePath,
        line: idx + 1,
        kind: "template-text",
        sample: text.slice(0, 80),
      });
    }
  });
  return findings;
}

function scanScript(lines, filePath) {
  const findings = [];
  let inScript = false;
  lines.forEach((line, idx) => {
    if (line.includes("<script")) {
      inScript = true;
      return;
    }
    if (line.includes("</script>")) inScript = false;
    if (!inScript) return;

    const matches = line.matchAll(/(['"`])((?:(?!\1).){2,120})\1/g);
    for (const match of matches) {
      const literal = match[2]?.trim() || "";
      if (line.includes("import ") && line.includes(" from ")) continue;
      if (line.includes(" key: ") || line.includes(" id: ")) continue;
      if (line.includes("message.includes(")) continue; // backend keyword matching
      if (/['"`][^'"`]+['"`]\s*:/.test(line)) continue; // object key/alias mapping
      if (!likelyUserCopy(literal)) continue;
      if (isLikelyTailwindClassLiteral(literal)) continue;
      if (literal === "message sent successfully") continue;
      // likely already localized or key-based usage
      if (literal.startsWith("common.") || literal.startsWith("chat.") || literal.startsWith("knowledge.")) continue;
      if (literal.includes("configCenter.") || literal.includes("documents.") || literal.includes("cases.")) continue;
      if (literal.includes("noopener noreferrer")) continue;
      if (literal.includes("<div class=") || literal.includes("<table")) continue;
      findings.push({
        filePath,
        line: idx + 1,
        kind: "script-literal",
        sample: literal.slice(0, 80),
      });
    }
  });
  return findings;
}

function main() {
  const files = TARGET_DIRS.flatMap((dir) => listVueFiles(path.join(SRC_DIR, dir)));
  const all = [];

  for (const filePath of files) {
    if (isUiPrimitiveFile(filePath)) continue;
    const content = fs.readFileSync(filePath, "utf8");
    const lines = splitLines(content);
    all.push(...scanTemplate(lines, filePath));
    all.push(...scanScript(lines, filePath));
  }

  if (!all.length) {
    console.log("No obvious hardcoded user-facing copy found.");
    return;
  }

  console.log(`Potential hardcoded copy findings: ${all.length}\n`);
  for (const item of all) {
    const rel = path.relative(ROOT, item.filePath).replaceAll("\\", "/");
    console.log(`[${item.kind}] ${rel}:${item.line} -> ${item.sample}`);
  }
}

main();
