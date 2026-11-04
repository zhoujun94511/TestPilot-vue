/**
 * Style conflict guardrails (double chrome, legacy hooks, clipped forms).
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
      if (name === "node_modules") continue;
      walk(full, acc);
    } else if (/\.(vue|ts)$/.test(name)) {
      acc.push(full);
    }
  }
  return acc;
}

function rel(file) {
  return path.relative(SRC, file).replaceAll("\\", "/");
}

const legacyFieldClass = /\b(tp-input|tp-select|tp-textarea)\b/;

for (const file of walk(SRC)) {
  const normalized = file.replaceAll("\\", "/");
  if (normalized.includes("/styles/tailwind.css")) continue;

  const content = fs.readFileSync(file, "utf8");
  const lines = content.split(/\r?\n/);

  lines.forEach((line, index) => {
    const ln = index + 1;

    if (legacyFieldClass.test(line) && /\.vue$/.test(file)) {
      issues.push({
        file: rel(file),
        line: ln,
        kind: "legacy-tp-field-class",
        hint: "改用 field-control variants 或 TpInput / TableFilter*"
      });
    }

    if (/resultItemClass/.test(line) && /panelShellClass/.test(line)) {
      issues.push({
        file: rel(file),
        line: ln,
        kind: "double-list-shell",
        hint: "列表项已有 resultItemClass，勿再叠 panelShellClass"
      });
    }

    if (/activityItemClass/.test(line) && /panelShellClass/.test(line)) {
      issues.push({
        file: rel(file),
        line: ln,
        kind: "double-list-shell",
        hint: "活动项已有 activityItemClass，勿再叠 panelShellClass"
      });
    }

    if (/PagePanel[^>]*>[\s\S]{0,200}<TpCard/.test(line)) {
      /* skip — multiline false positive on single line */
    }
  });

  if (
    /config-section-panel|CONFIG_SECTION_PANEL/.test(content) &&
    /overflow-hidden/.test(content) &&
    /config-ui\.ts$/.test(normalized)
  ) {
    issues.push({
      file: rel(file),
      line: 0,
      kind: "form-panel-overflow-hidden",
      hint: "配置分区勿 overflow-hidden，以免控件边框/focus 被裁切"
    });
  }

  if (/Card\.vue$/.test(normalized)) {
    if (/border border-border/.test(content) && /shadow-sm/.test(content)) {
      issues.push({
        file: rel(file),
        line: 0,
        kind: "card-primitive-chrome",
        hint: "Card 基元应无 border/shadow，外框由 TpCard/surfacePanelClass 提供"
      });
    }
  }
}

if (issues.length) {
  console.error(`Style conflict check failed (${issues.length}):`);
  for (const item of issues) {
    console.error(`  ${item.file}:${item.line} [${item.kind}] ${item.hint}`);
  }
  process.exit(1);
}

console.log("Style conflict check OK.");
