/**
 * White-box: Chat Markdown 渲染应产出表格包装与代码块复制按钮（与 ChatMessageContent 规则对齐）。
 */
import MarkdownIt from "markdown-it";

const t = (key) => {
  const map = {
    "chat.richContent.expand": "Expand",
    "chat.richContent.copy": "Copy",
    "chat.richContent.tableHint": "Scroll table"
  };
  return map[key] ?? key;
};

const markdown = new MarkdownIt({ html: false, linkify: true, breaks: true, typographer: false });
markdown.renderer.rules.table_open = () =>
  `<div class="chat-rich-content__table-wrap"><div class="chat-rich-content__table-hint">${t("chat.richContent.tableHint")}</div><table class="chat-rich-content__table">`;
markdown.renderer.rules.table_close = () => "</table></div>";

const sample = ["| A | B |", "| --- | --- |", "| 1 | 2 |", "", "```txt", "line1", "```"].join("\n");
const html = markdown.render(sample);

const checks = [
  ["table wrap", html.includes("chat-rich-content__table-wrap")],
  ["table hint", html.includes("chat-rich-content__table-hint")],
  ["code in pre", html.includes("<pre") && html.includes("line1")]
];

const failed = checks.filter(([, ok]) => !ok);
if (failed.length) {
  console.error("Markdown render white-box failed:");
  for (const [name] of failed) console.error(`  - missing ${name}`);
  process.exit(1);
}

console.log("Markdown render white-box OK.");
