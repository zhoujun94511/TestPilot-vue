# TestPilot 品牌标识

## 源与流水线

| 项 | 路径 |
|----|------|
| **主源** | `public/pic/examplepic.png` |
| 归档副本 | `src/assets/brand-source/brand-mark-raster-master.png`（`brand:icons` 同步） |
| 圆角 raster | `src/assets/brand-source/brand-app-raster-512.png`（蒙版中间产物，自动生成） |
| Chat 助手 | `src/assets/chat-assistant-robot.svg` → `public/tsvg/robot.svg` |

生成：`npm run brand:icons`（ICO 由 `scripts/write-ico.py` + Pillow 写入，保留 RGBA 透明）

## 应用内

| 项 | 说明 |
|----|------|
| `brand.ts` | `brand-mark.png` / `@2x` / `@3x`（圆角外透明，与 favicon 同源） |
| `BrandMark.vue` | 侧栏顶栏等 |
| `ChatAssistantAvatar.vue` | 对话内机器人头像（非品牌 mark） |
| `ChatUserAvatar.vue` | 对话内用户默认头像（Lucide User + 主色圆底） |

## 产出物

| 路径 | 用途 |
|------|------|
| `public/favicon.ico`、`public/pic/favicon.ico` | 浏览器 / Flask `/favicon.ico` |
| `public/favicon.svg`、`public/tsvg/testpilot-mark.svg` | SVG（带 clip，链 `favicon-512.png`） |
| `public/pic/favicon-256.png`、`favicon-512.png`、`favicon-1024.png` | PNG / README 展示 |
| `static/pic/*.ico` | PyInstaller |
| `public/tsvg/robot.svg` | 旧 URL 兼容 |

## favicon vs wavicon

- **favicon**：圆角标，角外透明；`index.html` 优先 PNG + ICO。
- **wavicon.ico**：同蒙版，尺寸档含 24px，供 Windows exe。
