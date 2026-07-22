<!-- Adapted from Vue Bits SpotlightCard by David Haz. MIT + Commons Clause. -->
<template>
  <article
    ref="cardRef"
    class="spotlight-card"
    @pointermove="moveSpotlight"
    @pointerenter="visible = true"
    @pointerleave="visible = false"
    @focusin="visible = true"
    @focusout="visible = false"
  >
    <span class="spotlight" :class="{ visible }" aria-hidden="true" />
    <div class="content"><slot /></div>
  </article>
</template>

<script setup>
import { ref } from 'vue'

const cardRef = ref(null)
const visible = ref(false)

function moveSpotlight(event) {
  const rect = cardRef.value.getBoundingClientRect()
  cardRef.value.style.setProperty('--spot-x', `${event.clientX - rect.left}px`)
  cardRef.value.style.setProperty('--spot-y', `${event.clientY - rect.top}px`)
}
</script>

<style scoped>
.spotlight-card {
  --spot-x: 50%;
  --spot-y: 50%;
  position: relative;
  overflow: hidden;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
}
.spotlight {
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0;
  background: radial-gradient(circle 280px at var(--spot-x) var(--spot-y), rgba(159, 226, 75, 0.13), transparent 70%);
  transition: opacity 220ms var(--ease-out);
}
.spotlight.visible { opacity: 1; }
.content { position: relative; height: 100%; }
@media (hover: none) { .spotlight { display: none; } }
</style>
