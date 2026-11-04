/** 应用内圆角标（与 public/favicon.ico 同蒙版） */
import brandMarkPngUrl from '@/assets/brand-mark.png';
import brandMark2xUrl from '@/assets/brand-mark@2x.png';
import brandMark3xUrl from '@/assets/brand-mark@3x.png';
import chatAssistantRobotUrl from '@/assets/chat-assistant-robot.svg';

/** 默认 512，侧栏/顶栏在 Retina 下仍清晰（圆角外透明） */
export const brandMarkSrc = brandMark2xUrl;

export const brandMarkSrcSet = `${brandMarkPngUrl} 256w, ${brandMark2xUrl} 512w, ${brandMark3xUrl} 1024w`;

/** Chat 空状态与助手消息头像（彩色机器人，与 Frame 品牌 mark 区分） */
export const chatAssistantRobotSrc = chatAssistantRobotUrl;

/** 仪表盘等活动列表里表示「使用 BrandMark 而非字母图标」 */
export const brandMarkIconKey = 'brand-mark' as const;
