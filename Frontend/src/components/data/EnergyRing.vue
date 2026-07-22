<template>
  <div class="energy-ring" :style="{ '--progress': `${progress * 3.6}deg` }" role="img" :aria-label="`${label} ${value} / ${total} ${unit}`">
    <div class="ring-core">
      <span>{{ label }}</span>
      <strong class="metric-number">{{ value.toLocaleString('zh-CN') }}</strong>
      <small>/ {{ total.toLocaleString('zh-CN') }} {{ unit }}</small>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({
  label: { type: String, default: '今日摄入' },
  value: { type: Number, required: true },
  total: { type: Number, required: true },
  unit: { type: String, default: 'kcal' },
})
const progress = computed(() => props.total > 0
  ? Math.min(Math.max(Math.round((props.value / props.total) * 100), 0), 100)
  : 0)
</script>

<style scoped>
.energy-ring {
  position: relative;
  width: clamp(220px, 24vw, 330px);
  aspect-ratio: 1;
  padding: 18px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: conic-gradient(var(--primary) var(--progress), rgba(255,255,255,.08) 0);
  box-shadow: 0 0 0 1px rgba(159,226,75,.08), 0 32px 80px rgba(2,7,3,.42);
  transform: rotate(-18deg);
}
.energy-ring::before {
  content: '';
  position: absolute;
  width: 3px;
  height: 18px;
  background: var(--accent);
  border-radius: 3px;
  transform: translateY(calc(clamp(220px, 24vw, 330px) / -2 + 8px)) rotate(18deg);
}
.ring-core {
  width: 100%;
  height: 100%;
  display: grid;
  place-content: center;
  text-align: center;
  background: radial-gradient(circle at 35% 25%, #20281e, var(--canvas-soft) 72%);
  border: 1px solid var(--border);
  border-radius: 50%;
  transform: rotate(18deg);
}
.ring-core span { color: var(--text-secondary); font-size: .78rem; }
.ring-core strong { margin: 6px 0 0; font-size: clamp(3.4rem, 6vw, 5.6rem); line-height: .84; font-weight: 600; letter-spacing: -.04em; }
.ring-core small { margin-top: 10px; color: var(--muted); font-size: .78rem; }
</style>
