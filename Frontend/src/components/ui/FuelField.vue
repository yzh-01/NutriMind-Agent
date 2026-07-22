<!-- Adapted from Uiverse Galaxy input by 0xnihilism. MIT. -->
<template>
  <label class="fuel-field">
    <span>{{ label }}</span>
    <input
      :value="modelValue"
      :type="type"
      :placeholder="placeholder"
      :autocomplete="autocomplete"
      :min="min"
      :max="max"
      @input="$emit('update:modelValue', $event.target.value)"
    />
    <small v-if="hint">{{ hint }}</small>
  </label>
</template>

<script setup>
defineProps({
  modelValue: { type: [String, Number], default: '' },
  label: { type: String, required: true },
  type: { type: String, default: 'text' },
  placeholder: { type: String, default: '' },
  autocomplete: { type: String, default: 'off' },
  hint: { type: String, default: '' },
  min: { type: [String, Number], default: undefined },
  max: { type: [String, Number], default: undefined },
})
defineEmits(['update:modelValue'])
</script>

<style scoped>
.fuel-field { display: grid; gap: 8px; color: var(--text-secondary); font-size: .86rem; font-weight: 500; }
.fuel-field input {
  width: 100%;
  min-height: 48px;
  padding: 0 14px;
  color: var(--text);
  background: var(--canvas-soft);
  border: 1px solid var(--border);
  border-radius: 10px;
  outline: none;
  box-shadow: 4px 4px 0 rgba(159, 226, 75, 0);
  transition: border-color 220ms var(--ease-out), box-shadow 220ms var(--ease-out), transform 220ms var(--ease-out);
}
.fuel-field input:focus { border-color: var(--primary); box-shadow: 4px 4px 0 rgba(159, 226, 75, .2); transform: translate(-1px, -1px); }
.fuel-field input::placeholder { color: var(--muted); }
.fuel-field small { color: var(--muted); font-size: .75rem; font-weight: 400; }
</style>
