<script setup lang="ts">
import type { DropdownMenuSubTriggerProps } from "reka-ui"
import type { HTMLAttributes } from "vue"
import { reactiveOmit } from "@vueuse/core"
import { ChevronRight } from "@lucide/vue"
import {
  DropdownMenuSubTrigger,
  useForwardProps,
} from "reka-ui"
import { dropdownMenuItemClass } from "@/lib/dropdown-ui"
import { cn } from "@/lib/utils"

const props = defineProps<DropdownMenuSubTriggerProps & { class?: HTMLAttributes["class"] }>()

const delegatedProps = reactiveOmit(props, "class")

const forwardedProps = useForwardProps(delegatedProps)
</script>

<template>
  <DropdownMenuSubTrigger
    v-bind="forwardedProps"
    :class="cn(
      'flex cursor-default select-none items-center px-2 py-1.5 outline-none',
      dropdownMenuItemClass,
      'data-[state=open]:bg-[var(--tp-accent)] data-[state=open]:text-[var(--tp-accent-foreground)]',
      props.class,
    )"
  >
    <slot />
    <ChevronRight class="ml-auto h-4 w-4" />
  </DropdownMenuSubTrigger>
</template>
