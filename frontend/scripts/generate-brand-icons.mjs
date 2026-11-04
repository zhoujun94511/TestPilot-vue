/**
 * 主源 examplepic → 圆角蒙版 raster → favicon / wavicon / brand-mark
 * 方底原图仅归档到 brand-mark-raster-master.png
 */
import {
  writeFileSync,
  mkdirSync,
  copyFileSync,
  existsSync,
  mkdtempSync,
  rmSync,
  readFileSync,
  unlinkSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { spawnSync } from 'node:child_process';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import sharp from 'sharp';

const __dirname = dirname(fileURLToPath(import.meta.url));
const frontendRoot = join(__dirname, '..');
const assets = join(frontendRoot, 'src/assets');
const brandSource = join(assets, 'brand-source');

const EXAMPLE_PIC = join(frontendRoot, 'public/pic/examplepic.png');
const RASTER_HD = join(brandSource, 'brand-mark-raster-master.png');
const APP_MASTER = join(brandSource, 'brand-app-raster-512.png');

/** 与 examplepic 圆角视觉对齐，略加大以便 16–32px 仍看得出圆角 */
const CORNER_RX = 11 / 32;

function resolveWebRaster() {
  if (existsSync(EXAMPLE_PIC)) {
    return EXAMPLE_PIC;
  }
  if (existsSync(RASTER_HD)) {
    return RASTER_HD;
  }
  throw new Error('缺少 public/pic/examplepic.png（或先运行 brand:icons 生成 brand-mark-raster-master.png）');
}

async function roundedMaskPng(size) {
  const r = size * CORNER_RX;
  const maskSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}"><rect width="${size}" height="${size}" rx="${r}" fill="#ffffff"/></svg>`;
  return sharp(Buffer.from(maskSvg)).png().toBuffer();
}

/** @param {string} masterPath @param {number} size */
async function rasterizeWeb(masterPath, size) {
  return sharp(masterPath)
    .resize(size, size, { fit: 'fill', kernel: sharp.kernel.lanczos3 })
    .ensureAlpha()
    .png({ compressionLevel: 9, effort: 10, palette: false })
    .toBuffer();
}

async function rasterizeApp(size) {
  return sharp(APP_MASTER)
    .resize(size, size, { fit: 'fill', kernel: sharp.kernel.lanczos3 })
    .ensureAlpha()
    .png({ compressionLevel: 9, effort: 10, palette: false })
    .toBuffer();
}

const WRITE_ICO_PY = join(__dirname, 'write-ico.py');

/** @param {string} outPath @param {Buffer[]} pngBuffers @param {number[]} sizes */
function writeIcoWithPillow(outPath, pngBuffers, sizes) {
  const tmp = mkdtempSync(join(tmpdir(), 'testpilot-ico-'));
  const tmpIco = join(tmp, 'out.ico');
  try {
    const paths = sizes.map((s, i) => {
      const p = join(tmp, `${s}.png`);
      writeFileSync(p, pngBuffers[i]);
      return p;
    });
    const r = spawnSync('python', [WRITE_ICO_PY, tmpIco, ...paths], {
      encoding: 'utf8',
    });
    if (r.status !== 0) {
      throw new Error(
        `write-ico.py failed: ${r.stderr?.trim() || r.stdout?.trim() || r.status}`,
      );
    }
    const icoBytes = readFileSync(tmpIco);
    if (existsSync(outPath)) {
      try {
        unlinkSync(outPath);
      } catch {
        /* 可能被资源管理器占用，仍尝试覆盖写入 */
      }
    }
    writeFileSync(outPath, icoBytes);
  } finally {
    rmSync(tmp, { recursive: true, force: true });
  }
}

function writeFaviconSvgRasterLink() {
  const rx = 512 * CORNER_RX;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 512 512" role="img" aria-label="TestPilot">
  <defs>
    <clipPath id="tp-mark-clip"><rect width="512" height="512" rx="${rx}" ry="${rx}"/></clipPath>
  </defs>
  <image width="512" height="512" clip-path="url(#tp-mark-clip)" xlink:href="/pic/favicon-512.png"/>
</svg>`;
  writeFileSync(join(frontendRoot, 'public/favicon.svg'), svg);
  writeFileSync(join(frontendRoot, 'public/tsvg/testpilot-mark.svg'), svg);
}

const webRaster = resolveWebRaster();

async function ensureAppMaster() {
  const base512 = await rasterizeWeb(webRaster, 512);
  const mask512 = await roundedMaskPng(512);
  const png = await sharp(base512)
    .composite([{ input: mask512, blend: 'dest-in' }])
    .png({ compressionLevel: 9, effort: 10, palette: false })
    .toBuffer();
  writeFileSync(APP_MASTER, png);
}

await ensureAppMaster();

const faviconSizes = [16, 32, 48, 64, 128, 256];
const appIconSizes = [16, 24, 32, 48, 64, 128, 256];

const faviconPngs = await Promise.all(faviconSizes.map((s) => rasterizeApp(s)));
const appIconPngs = await Promise.all(appIconSizes.map((s) => rasterizeApp(s)));
const meta = await sharp(webRaster).metadata();
const masterSide = Math.min(2048, Math.max(meta.width ?? 1024, meta.height ?? 1024));
const appMarkSide = Math.min(1024, masterSide);
const appPng512 = await rasterizeApp(512);
const appPng1024 = await rasterizeApp(appMarkSide);
const appPng256 = faviconPngs[faviconSizes.indexOf(256)];
const appPngMaster = appPng1024;

const picDir = join(frontendRoot, 'public/pic');
mkdirSync(picDir, { recursive: true });

const faviconIcoPath = join(picDir, 'favicon.ico');
const waviconIcoPath = join(picDir, 'wavicon.ico');
writeIcoWithPillow(faviconIcoPath, faviconPngs, faviconSizes);
writeIcoWithPillow(waviconIcoPath, appIconPngs, appIconSizes);
copyFileSync(faviconIcoPath, join(frontendRoot, 'public/favicon.ico'));
writeFileSync(join(picDir, 'favicon-256.png'), faviconPngs[faviconSizes.indexOf(256)]);
writeFileSync(join(picDir, 'favicon-512.png'), appPng512);
writeFileSync(join(picDir, 'favicon-1024.png'), appPng1024);

writeFileSync(join(assets, 'brand-mark.png'), appPng256);
writeFileSync(join(assets, 'brand-mark@2x.png'), appPng512);
writeFileSync(join(assets, 'brand-mark@3x.png'), appPngMaster);

if (webRaster !== RASTER_HD) {
  mkdirSync(brandSource, { recursive: true });
  copyFileSync(webRaster, RASTER_HD);
}

writeFaviconSvgRasterLink();

const repoStaticPic = join(frontendRoot, '..', 'static', 'pic');
mkdirSync(repoStaticPic, { recursive: true });
copyFileSync(join(picDir, 'favicon.ico'), join(repoStaticPic, 'favicon.ico'));
copyFileSync(join(picDir, 'wavicon.ico'), join(repoStaticPic, 'wavicon.ico'));

const masterLabel = webRaster.endsWith('examplepic.png')
  ? 'public/pic/examplepic.png'
  : 'brand-mark-raster-master.png';
console.log(`${masterLabel} → 圆角 favicon / wavicon / brand-mark (${masterSide}px 归档)`);
