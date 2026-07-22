<!-- Adapted from Uiverse Galaxy button by 0x-Sarthak. MIT. -->
<template>
  <button :type="nativeType" class="fuel-button" :class="[`is-${variant}`, { loading }]" :disabled="disabled || loading">
    <span class="wash" aria-hidden="true" />
    <span class="label"><slot /></span>
    <CircleNotch v-if="loading" class="spinner" :size="18" weight="bold" aria-hidden="true" />
    <ArrowUpRight v-else-if="arrow" class="arrow" :size="18" weight="bold" aria-hidden="true" />
  </button>
</template>

<script setup>
import { PhArrowUpRight as ArrowUpRight, PhCircleNotch as CircleNotch } from '@phosphor-icons/vue'

defineProps({
  variant: { type: String, default: 'primary' },
  nativeType: { type: String, default: 'button' },
  loading: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  arrow: { type: Boolean, default: true },
})
</script>

<style scoped>
.fuel-button {
  position: relative;
  isolation: isolate;
  min-height: 48px;
  padding: 0 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  overflow: hidden;
  color: #11160f;
  background: var(--primary);
  border: 1px solid var(--primary);
  border-radius: 10px;
  font-weight: 600;
  transition: transform 180ms var(--ease-out), border-color 220ms var(--ease-out), color 220ms var(--ease-out);
}
.wash {
  position: absolute;
  z-index: -1;
  inset: 0;
  background: #f0f5ed;
  transform: translateX(102%);
  transition: transform 420ms var(--ease-out);
}
.fuel-button:hover .wash { transform: translateX(0); }
.fuel-button:active { transform: scale(.98); }
.fuel-button:disabled { opacity: .5; transform: none; }
.is-secondary { color: var(--text); background: transparent; border-color: var(--border-strong); }
.is-secondary .wash { background: var(--surface-soft); }
.is-danger { color: #fff; background: var(--danger); border-color: var(--danger); }
.label { position: relative; white-space: nowrap; }
.arrow { transition: transform 260ms var(--ease-out); }
.fuel-button:hover .arrow { transform: translate(2px, -2px); }
.spinner { animation: spin 800ms linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
