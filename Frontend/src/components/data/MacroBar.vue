<template>
  <div class="macro">
    <div><span>{{ label }}</span><strong class="metric-number">{{ value }} / {{ total }}g</strong></div>
    <div class="bar" role="progressbar" :aria-label="label" :aria-valuenow="value" :aria-valuemax="total"><i :style="{ transform: `scaleX(${ratio})` }" /></div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ label: String, value: Number, total: Number })
const ratio = computed(() => Math.min(props.value / props.total, 1))
</script>

<style scoped>
.macro { display: grid; gap: 9px; }
.macro > div:first-child { display: flex; justify-content: space-between; gap: 12px; color: var(--text-secondary); font-size: .83rem; }
.macro strong { color: var(--text); font-size: 1rem; font-weight: 500; }
.bar { height: 4px; overflow: hidden; background: rgba(255,255,255,.08); border-radius: 3px; }
.bar i { width: 100%; height: 100%; display: block; background: var(--primary); border-radius: inherit; transform-origin: left; transition: transform 700ms var(--ease-out); }
</style>
