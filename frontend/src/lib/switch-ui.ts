import { cva } from 'class-variance-authority';

export const switchFieldRoot = cva('inline-flex w-fit min-w-[120px] items-center');

export const switchComposerRoot = cva(
  'group/switch inline-flex cursor-pointer select-none items-center gap-2 rounded-full border border-transparent px-1 py-0.5 transition-colors',
  {
    variants: {
      on: {
        /** 开/关仅由轨道与徽章表达，避免整行底色 + 轨道外发光叠成「双选中」 */
        true: '',
        false: ''
      },
      disabled: {
        true: 'cursor-not-allowed opacity-60',
        false: ''
      }
    }
  }
);

export const switchLabelInner = cva(
  'group/switch inline-flex cursor-pointer select-none items-center gap-2 rounded-full px-1 py-0.5 transition-colors duration-tp-fast peer-focus-visible:rounded-full peer-focus-visible:outline-none peer-focus-visible:ring-2 peer-focus-visible:ring-inset peer-focus-visible:ring-ring',
  {
    variants: {
      on: {
        true: 'bg-[color-mix(in_srgb,var(--tp-color-primary-500)_8%,var(--tp-bg-surface)_92%)]',
        false: 'bg-[color-mix(in_srgb,var(--tp-bg-surface)_88%,var(--tp-border-default)_12%)]'
      }
    }
  }
);

export const switchTrack = cva(
  'relative h-7 w-12 shrink-0 rounded-full border border-[var(--tp-border-default)] bg-[color-mix(in_srgb,var(--tp-muted)_88%,var(--tp-bg-surface))] transition-[background-color,border-color] group-has-[:focus-visible]/switch:ring-2 group-has-[:focus-visible]/switch:ring-inset group-has-[:focus-visible]/switch:ring-ring',
  {
    variants: {
      on: {
        true: 'border-transparent bg-[var(--tp-color-primary-500)]',
        false: ''
      }
    }
  }
);

export const switchThumb = cva(
  'absolute left-[3px] top-[3px] h-5 w-5 rounded-full bg-[var(--tp-bg-surface)] shadow-[var(--tp-shadow-switch-knob)] transition-transform',
  {
    variants: {
      on: {
        true: 'translate-x-5',
        false: ''
      }
    }
  }
);

export const switchStateBadge = cva(
  'min-w-[34px] rounded-full border px-1.5 py-1 text-center text-[11px] font-bold leading-none',
  {
    variants: {
      on: {
        true: 'border-[color-mix(in_srgb,var(--tp-color-primary-500)_60%,transparent)] bg-[color-mix(in_srgb,var(--tp-color-primary-500)_20%,transparent)] text-[var(--tp-color-primary-700)]',
        false: 'border-[color-mix(in_srgb,var(--tp-color-text-300)_70%,transparent)] bg-[color-mix(in_srgb,var(--tp-color-text-200)_60%,transparent)] text-[var(--tp-color-text-500)]'
      }
    }
  }
);

export const switchCaption = cva(
  'whitespace-nowrap text-sm font-semibold text-[var(--tp-color-text-600)]'
);
