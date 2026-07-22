<!-- Adapted from Vue Bits CountUp by David Haz. MIT + Commons Clause. -->
<template><span ref="elementRef" class="count-up">{{ display }}</span></template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  to: { type: Number, required: true },
  from: { type: Number, default: 0 },
  duration: { type: Number, default: 900 },
  decimals: { type: Number, default: 0 },
  suffix: { type: String, default: '' },
})

const elementRef = ref(null)
const display = ref('0')
let frameId = 0
let observer

function format(value) {
  return `${new Intl.NumberFormat('zh-CN', {
    minimumFractionDigits: props.decimals,
    maximumFractionDigits: props.decimals,
  }).format(value)}${props.suffix}`
}

function animate() {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    display.value = format(props.to)
    return
  }
  const startedAt = performance.now()
  const distance = props.to - props.from
  const tick = (now) => {
    const progress = Math.min((now - startedAt) / props.duration, 1)
    const eased = 1 - Math.pow(1 - progress, 3)
    display.value = format(props.from + distance * eased)
    if (progress < 1) frameId = requestAnimationFrame(tick)
  }
  frameId = requestAnimationFrame(tick)
}

function observe() {
  observer = new IntersectionObserver(([entry]) => {
    if (!entry.isIntersecting) return
    animate()
    observer.disconnect()
  })
  observer.observe(elementRef.value)
}

watch(() => props.to, () => {
  cancelAnimationFrame(frameId)
  animate()
})

onMounted(observe)
onBeforeUnmount(() => {
  cancelAnimationFrame(frameId)
  observer?.disconnect()
})
</script>

<style scoped>
.count-up { font-variant-numeric: tabular-nums; }
</style>
