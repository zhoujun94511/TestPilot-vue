import { cn } from '@/lib/utils';

export type BrandMarkSize = 'xs' | 'sm' | 'md' | 'lg';

const sizeMap: Record<BrandMarkSize, string> = {
  xs: 'h-5 w-5',
  sm: 'h-6 w-6',
  md: 'h-8 w-8',
  lg: 'h-10 w-10'
};

export function brandMarkSizeClass(size: BrandMarkSize) {
  return cn('block shrink-0 object-contain', sizeMap[size]);
}

/** 仅 BrandMark：圆角 PNG 留透明边，勿用于 Chat 机器人 SVG */
export const brandMarkInsetClass = 'p-[11%]';

export function chatAssistantAvatarSizeClass(size: BrandMarkSize) {
  return brandMarkSizeClass(size);
}

/** 实心主色圆标 + 浅色剪影，浅色/深色都用同一套近白色，不跟 text-inverse 反转 */
export function chatUserAvatarShellClass(size: BrandMarkSize) {
  return cn(
    brandMarkSizeClass(size),
    'inline-flex items-center justify-center overflow-hidden rounded-full',
    'bg-[linear-gradient(165deg,color-mix(in_srgb,var(--tp-color-primary-600)_70%,white)_0%,var(--tp-color-primary-600)_46%,var(--tp-color-primary-700)_100%)]',
    'text-[#f8fafc]',
    'shadow-[inset_0_0_0_1px_color-mix(in_srgb,white_32%,transparent)]'
  );
}
