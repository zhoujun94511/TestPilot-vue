/**
 * Heuristic display/consistency checks (white-box, best-effort).
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC = path.join(path.resolve(__dirname, ".."), "src");

const issues = [];

function walk(dir, acc = []) {
  for (const name of fs.readdirSync(dir)) {
    const full = path.join(dir, name);
    if (fs.statSync(full).isDirectory()) {
      if (name === "node_modules" || name === "ui") continue;
      walk(full, acc);
    } else if (name.endsWith(".vue")) {
      acc.push(full);
    }
  }
  return acc;
}

function rel(file) {
  return path.relative(SRC, file).replaceAll("\\", "/");
}

function blockHasTitle(lines, startIndex, span = 6) {
  const chunk = lines.slice(startIndex, startIndex + span).join("\n");
  return /:title=/.test(chunk) || /\btitle=/.test(chunk);
}

for (const file of walk(SRC)) {
  const lines = fs.readFileSync(file, "utf8").split(/\r?\n/);
  lines.forEach((line, index) => {
    const ln = index + 1;
    if (/\btruncate\b/.test(line) && !blockHasTitle(lines, index)) {
      if (line.includes("TableHead") || line.includes("TpButton")) return;
      issues.push({
        file: rel(file),
        line: ln,
        kind: "truncate-without-title",
        hint: "长文本 truncate 建议同级提供 title/tooltip，避免用户看不到全文"
      });
    }
    if (/\bline-clamp-\d\b/.test(line) && !blockHasTitle(lines, index)) {
      if (line.includes("TpButton")) return;
      issues.push({
        file: rel(file),
        line: ln,
        kind: "line-clamp-without-title",
        hint: "line-clamp 截断建议提供 title 以便 hover 查看全文"
      });
    }
    if (/v-html=/.test(line) && !file.replaceAll("\\", "/").includes("ChatMessageContent.vue")) {
      issues.push({
        file: rel(file),
        line: ln,
        kind: "v-html-outside-chat",
        hint: "非 Chat 富文本组件使用 v-html，需确认已消毒"
      });
    }
    if (/#[0-9a-fA-F]{3,8}\b/.test(line) && !file.includes("notice-ui")) {
      issues.push({
        file: rel(file),
        line: ln,
        kind: "hardcoded-hex-in-vue",
        hint: "视图层硬编码色值，优先 tokens / notice-ui 集中定义"
      });
    }
  });
}

const blocking = issues.filter((i) => i.kind === "v-html-outside-chat" || i.kind === "hardcoded-hex-in-vue");

if (issues.length) {
  console.log("Display pattern report (informational + blocking):");
  for (const item of issues) {
    const level = blocking.includes(item) ? "ERROR" : "WARN";
    console.log(`[${level}] ${item.file}:${item.line} ${item.kind} — ${item.hint}`);
  }
}

if (blocking.length) {
  process.exit(1);
}

const warnCount = issues.length;
if (warnCount > 0) {
  process.exit(1);
}

console.log(`Display pattern check OK (0 warnings, 0 blocking).`);
