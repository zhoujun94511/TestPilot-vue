/**
 * 同步 Chat 机器人兼容路径；Web/打包品牌由 generate-brand-icons.mjs 从 brand-source 生成
 * 由 npm run brand:icons 自动调用
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const frontendRoot = join(__dirname, '..');
const assets = join(frontendRoot, 'src/assets');

const robotPath = join(assets, 'chat-assistant-robot.svg');
writeFileSync(join(frontendRoot, 'public/tsvg/robot.svg'), readFileSync(robotPath, 'utf8'));

console.log('Synced public/tsvg/robot.svg <- chat-assistant-robot.svg');
