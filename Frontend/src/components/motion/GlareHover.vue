<!-- Adapted from Vue Bits GlareHover by David Haz. MIT + Commons Clause. -->
<template>
  <div class="glare-hover" @pointerenter="active = true" @pointerleave="active = false">
    <span :class="{ active }" aria-hidden="true" />
    <slot />
  </div>
</template>

<script setup>
import { ref } from 'vue'
const active = ref(false)
</script>

<style scoped>
.glare-hover { position: relative; overflow: hidden; }
.glare-hover > span {
  position: absolute;
  z-index: 2;
  inset: -70%;
  pointer-events: none;
  background: linear-gradient(115deg, transparent 38%, rgba(255,255,255,.22) 49%, transparent 60%);
  transform: translate3d(-58%, 38%, 0);
  transition: transform 700ms var(--ease-out);
}
.glare-hover > span.active { transform: translate3d(58%, -38%, 0); }
@media (prefers-reduced-motion: reduce), (hover: none) { .glare-hover > span { display: none; } }
</style>
