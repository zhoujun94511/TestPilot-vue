/**
 * i18n health check for current project structure:
 * - compare src/i18n/<locale>/*.ts against reference locale (en)
 * - same namespace files
 * - same key paths and value types
 * - exits with code 1 on mismatch
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const I18N_DIR = path.join(ROOT, "src", "i18n");
const SRC_DIR = path.join(ROOT, "src");
const REFERENCE_LOCALE = "en";

/** 与 src/i18n/index.ts 中 messages 的 namespace 一致（文件名 ≠ message 前缀时在此映射） */
const MESSAGE_NAMESPACE_BY_FILE = {
  "config-center.ts": "configCenter",
  "experimental-tools-page.ts": "experimentalToolsPage",
};

/** 代码中以模板/配置键动态拼接的 prefix，源码中出现 prefix 即视为已引用 */
const DYNAMIC_MESSAGE_PREFIXES = [
  "configCenter.itemLabel.",
  "configCenter.itemDescription.",
  "configCenter.category.",
  "configCenter.categoryDescription.",
  "configCenter.provider.",
  "configCenter.providerUi.",
  "enums.",
  "ai.",
  "admin.users.audit.events.",
  "admin.users.audit.details.fields.",
  "chat.experimentalTools.risk.",
  "chat.experimentalTools.fields.",
  "chat.experimentalTools.tools.",
  "chat.experimentalTools.toolDesc.",
  "chat.experimentalTools.placeholders.",
  "chat.toolMarkdown.scenario.",
  "chat.toolMarkdown.issue.",
  "chat.toolMarkdown.trace.",
  "chat.toolMarkdown.msg.",
  "dashboard.activities.messages.",
  "config.form.dedupWeights.",
];

function messageNamespaceForFile(fileName) {
  return MESSAGE_NAMESPACE_BY_FILE[fileName] || fileName.replace(/\.ts$/, "");
}

function loadReservedKeys() {
  const reservedPath = path.join(__dirname, "i18n-reserved-keys.json");
  if (!fs.existsSync(reservedPath)) return new Set();
  try {
    const list = JSON.parse(fs.readFileSync(reservedPath, "utf8"));
    return new Set(Array.isArray(list) ? list : []);
  } catch {
    return new Set();
  }
}

const RESERVED_KEYS = loadReservedKeys();

function isKeyReferenced(fullKey, sourceContent) {
  if (RESERVED_KEYS.has(fullKey)) return true;

  const quoted = [`t('${fullKey}')`, `t("${fullKey}")`, `'${fullKey}'`, `"${fullKey}"`];
  if (quoted.some((needle) => sourceContent.includes(needle))) return true;
  if (sourceContent.includes(fullKey)) return true;

  if (sourceContent.includes("translateKey(") && fullKey.startsWith("configCenter.")) {
    if (sourceContent.includes("configCenter.")) return true;
  }
  if (sourceContent.includes("translateEnum(") && fullKey.startsWith("enums.")) {
    const parts = fullKey.split(".");
    if (parts.length >= 4) {
      const enumPrefix = `${parts[0]}.${parts[1]}.${parts[2]}.`;
      if (sourceContent.includes(enumPrefix)) return true;
    }
  }
  if (sourceContent.includes("descriptionKey:") && fullKey.includes("providerUi.modelDescriptions.")) {
    return true;
  }
  if (sourceContent.includes("nameKey:") && fullKey.startsWith("configCenter.provider")) {
    return true;
  }

  for (const prefix of DYNAMIC_MESSAGE_PREFIXES) {
    if (fullKey.startsWith(prefix) && sourceContent.includes(prefix)) return true;
  }

  return false;
}

function valueType(value) {
  if (value === null) return "null";
  if (Array.isArray(value)) return "array";
  return typeof value;
}

function collectKeys(obj, prefix = "") {
  const output = new Map();
  if (obj === null || typeof obj !== "object" || Array.isArray(obj)) {
    output.set(prefix || "(root)", valueType(obj));
    return output;
  }
  for (const key of Object.keys(obj)) {
    const nextPath = prefix ? `${prefix}.${key}` : key;
    const val = obj[key];
    if (val && typeof val === "object" && !Array.isArray(val)) {
      const nested = collectKeys(val, nextPath);
      for (const [k, t] of nested) output.set(k, t);
    } else {
      output.set(nextPath, valueType(val));
    }
  }
  return output;
}

function listLocaleDirs() {
  if (!fs.existsSync(I18N_DIR)) return {};
  const dirs = fs
    .readdirSync(I18N_DIR)
    .filter((name) => fs.statSync(path.join(I18N_DIR, name)).isDirectory());
  const map = {};
  for (const dir of dirs) {
    map[dir] = path.join(I18N_DIR, dir);
  }
  return map;
}

function listLocaleTsFiles(localeDir) {
  if (!fs.existsSync(localeDir)) return [];
  return fs
    .readdirSync(localeDir)
    .filter((name) => name.endsWith(".ts") && name !== "index.ts")
    .sort();
}

function loadTsDefaultObject(filePath) {
  const raw = fs.readFileSync(filePath, "utf8");
  const normalized = raw.replace(/^\uFEFF/, "").trim();
  const exportDefaultMatch = normalized.match(/export\s+default\s+([\s\S]*?);?\s*$/);
  if (!exportDefaultMatch) {
    throw new Error(`Cannot parse default export object: ${filePath}`);
  }
  const objectLiteral = exportDefaultMatch[1];
  try {
    // eslint-disable-next-line no-new-func
    const loader = new Function(`return (${objectLiteral});`);
    return loader();
  } catch (error) {
    throw new Error(`Invalid locale object in ${filePath}: ${error.message}`);
  }
}

function listSourceFiles(dir, acc = []) {
  if (!fs.existsSync(dir)) return acc;
  for (const name of fs.readdirSync(dir)) {
    const full = path.join(dir, name);
    const stat = fs.statSync(full);
    if (stat.isDirectory()) {
      if (name !== "i18n" && name !== "node_modules") listSourceFiles(full, acc);
      continue;
    }
    if ((name.endsWith(".ts") || name.endsWith(".tsx") || name.endsWith(".vue")) && !name.endsWith(".d.ts")) {
      acc.push(full);
    }
  }
  return acc;
}

function listPythonFiles(dir, acc = []) {
  if (!fs.existsSync(dir)) return acc;
  for (const name of fs.readdirSync(dir)) {
    if (name === ".venv" || name === "node_modules" || name === "__pycache__" || name === "dist" || name === ".git") {
      continue;
    }
    const full = path.join(dir, name);
    const stat = fs.statSync(full);
    if (stat.isDirectory()) {
      listPythonFiles(full, acc);
      continue;
    }
    if (name.endsWith(".py")) acc.push(full);
  }
  return acc;
}

function reportPossiblyUnusedKeys(refFiles, refDir, options) {
  const verbose = options?.verbose === true;
  const allKeys = [];
  for (const file of refFiles) {
    const namespace = messageNamespaceForFile(file);
    const obj = loadTsDefaultObject(path.join(refDir, file));
    const keys = collectKeys(obj);
    for (const [keyPath] of keys) {
      if (keyPath === "(root)") continue;
      allKeys.push(`${namespace}.${keyPath}`);
    }
  }
  const sourceFiles = listSourceFiles(SRC_DIR);
  let sourceContent = "";
  for (const sourceFile of sourceFiles) {
    sourceContent += `${fs.readFileSync(sourceFile, "utf8")}\n`;
  }
  const repoRoot = path.resolve(ROOT, "..");
  for (const sourceFile of listPythonFiles(repoRoot)) {
    sourceContent += `${fs.readFileSync(sourceFile, "utf8")}\n`;
  }

  const maybeUnused = allKeys.filter((fullKey) => !isKeyReferenced(fullKey, sourceContent));
  if (!maybeUnused.length) return;
  console.log(`\n--- 可能未使用的 key: ${maybeUnused.length} 个（仅供参考）---`);
  if (verbose) {
    maybeUnused.forEach((key) => console.log(`  ${key}`));
  } else {
    console.log("  使用 npm run i18n:check -- --verbose 查看完整列表");
  }
}

function main() {
  const localeDirs = listLocaleDirs();
  const locales = Object.keys(localeDirs);
  if (!locales.length) {
    console.error("未找到任何 i18n locale 目录。");
    process.exit(1);
  }
  if (!localeDirs[REFERENCE_LOCALE]) {
    console.error(`未找到参考语言目录: ${REFERENCE_LOCALE}`);
    process.exit(1);
  }

  console.log(`i18n health check (reference: ${REFERENCE_LOCALE})\n`);

  const errors = [];
  const refFiles = listLocaleTsFiles(localeDirs[REFERENCE_LOCALE]);
  let totalKeys = 0;

  for (const locale of locales) {
    if (locale === REFERENCE_LOCALE) continue;
    const localeFiles = listLocaleTsFiles(localeDirs[locale]);
    const missingFiles = refFiles.filter((f) => !localeFiles.includes(f));
    const extraFiles = localeFiles.filter((f) => !refFiles.includes(f));
    if (missingFiles.length) errors.push({ kind: "missing_file", locale, files: missingFiles });
    if (extraFiles.length) errors.push({ kind: "extra_file", locale, files: extraFiles });
  }

  for (const file of refFiles) {
    const namespace = file.replace(/\.ts$/, "");
    const refPath = path.join(localeDirs[REFERENCE_LOCALE], file);
    const refObj = loadTsDefaultObject(refPath);
    const refKeys = collectKeys(refObj);
    totalKeys += refKeys.size;

    for (const locale of locales) {
      if (locale === REFERENCE_LOCALE) continue;
      const localePath = path.join(localeDirs[locale], file);
      if (!fs.existsSync(localePath)) continue;
      const localeObj = loadTsDefaultObject(localePath);
      const localeKeys = collectKeys(localeObj);

      for (const [keyPath, refType] of refKeys) {
        if (!localeKeys.has(keyPath)) {
          errors.push({ kind: "missing_key", locale, namespace, key: keyPath });
        } else {
          const localeType = localeKeys.get(keyPath);
          if (localeType !== refType) {
            errors.push({ kind: "type_mismatch", locale, namespace, key: keyPath, refType, localeType });
          }
        }
      }

      for (const keyPath of localeKeys.keys()) {
        if (!refKeys.has(keyPath)) {
          errors.push({ kind: "extra_key", locale, namespace, key: keyPath });
        }
      }
    }
  }

  if (errors.length) {
    console.log("--- 检查失败 ---\n");
    for (const error of errors) {
      if (error.kind === "missing_file") {
        console.log(`[${error.locale}] 缺失文件: ${error.files.join(", ")}`);
      } else if (error.kind === "extra_file") {
        console.log(`[${error.locale}] 多余文件: ${error.files.join(", ")}`);
      } else if (error.kind === "missing_key") {
        console.log(`[${error.locale}] ${error.namespace}.${error.key} 缺失`);
      } else if (error.kind === "extra_key") {
        console.log(`[${error.locale}] ${error.namespace}.${error.key} 多余`);
      } else if (error.kind === "type_mismatch") {
        console.log(`[${error.locale}] ${error.namespace}.${error.key} 类型不一致: ${REFERENCE_LOCALE}=${error.refType}, ${error.locale}=${error.localeType}`);
      }
    }
    process.exit(1);
  }

  console.log("--- 检查通过 ---");
  console.log(`  locale 数量: ${locales.length}`);
  console.log(`  namespace 数量: ${refFiles.length}`);
  console.log(`  总 key 数 (参考语言): ${totalKeys}`);
  reportPossiblyUnusedKeys(refFiles, localeDirs[REFERENCE_LOCALE], {
    verbose: process.argv.includes("--verbose"),
  });
  console.log("\nSummary: 成功");
}

main();
