<template>
  <main class="auth-shell">
    <section class="visual-side" aria-label="NutriMind Performance Fuel">
      <img
        src="https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=1600&q=82"
        width="1600"
        height="1200"
        alt="色彩丰富的健康餐食"
      />
      <div class="visual-scrim" />
      <router-link class="brand" to="/login"><Lightning :size="22" weight="fill" /> NutriMind</router-link>
      <div class="manifesto">
        <span class="status-chip">Performance Fuel</span>
        <h1>
          <span>练得更强，</span>
          <span>也要吃得更好。</span>
        </h1>
        <p>把减脂目标、训练安排和每一餐放到同一个计划里。</p>
      </div>
      <div class="fuel-preview surface">
        <div><small>训练日预算</small><strong class="metric-number">2,140 <i>kcal</i></strong></div>
        <span>蛋白质 150g</span><span>剩余 680 kcal</span>
      </div>
    </section>

    <section class="form-side">
      <div class="mobile-brand"><Lightning :size="22" weight="fill" /> NutriMind</div>
      <div class="form-wrap"><slot /></div>
      <p class="privacy"><LockKey :size="15" weight="bold" /> 使用安全会话保护账户数据</p>
    </section>
  </main>
</template>

<script setup>
import { PhLightning as Lightning, PhLockKey as LockKey } from '@phosphor-icons/vue'
</script>

<style lang="scss" scoped>
.auth-shell { min-height: 100dvh; display: grid; grid-template-columns: minmax(0, 1.15fr) minmax(430px, .85fr); background: var(--canvas); }
.visual-side { position: relative; min-height: 100dvh; padding: clamp(28px, 4vw, 58px); display: flex; flex-direction: column; overflow: hidden; }
.visual-side > img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; object-position: 50% 55%; }
.visual-scrim { position: absolute; inset: 0; background: linear-gradient(105deg, rgba(5,8,6,.96) 0%, rgba(5,8,6,.72) 48%, rgba(5,8,6,.2) 100%), linear-gradient(0deg, rgba(5,8,6,.85), transparent 55%); }
.brand, .manifesto, .fuel-preview { position: relative; }
.brand { display: inline-flex; align-items: center; gap: 9px; font-family: "Barlow Condensed"; font-size: 1.25rem; font-weight: 700; }
.brand :deep(svg) { color: var(--primary); }
.manifesto { width: min(760px, 100%); margin: auto 0; }
.manifesto h1 { margin: 26px 0 22px; font-family: MiSans, "HarmonyOS Sans SC", "Microsoft YaHei", sans-serif; font-size: clamp(3.5rem, 6vw, 6.4rem); font-weight: 700; line-height: 1.02; letter-spacing: -.012em; }
.manifesto h1 span { display: block; white-space: nowrap; }
.manifesto p { max-width: 34ch; margin: 0; color: #d1d9cf; font-size: clamp(1rem, 1.4vw, 1.25rem); line-height: 1.65; }
.fuel-preview { width: min(420px, 100%); padding: 16px 18px; display: grid; grid-template-columns: 1fr auto; align-items: end; gap: 8px 22px; background: rgba(14,18,15,.82); backdrop-filter: blur(12px); }
.fuel-preview div { grid-column: 1 / -1; display: flex; align-items: end; justify-content: space-between; }
.fuel-preview small, .fuel-preview span { color: #b7c0b7; font-size: .73rem; }
.fuel-preview strong { font-size: 2.25rem; line-height: 1; }
.fuel-preview i { color: var(--primary); font-size: .8rem; font-style: normal; font-weight: 500; }
.form-side { min-height: 100dvh; padding: 32px; display: flex; flex-direction: column; align-items: center; justify-content: center; background: radial-gradient(circle at 80% 20%, rgba(159,226,75,.07), transparent 24rem); }
.form-wrap { width: min(430px, 100%); }
.mobile-brand { display: none; }
.privacy { margin: 24px 0 0; display: flex; align-items: center; gap: 7px; color: var(--muted); font-size: .72rem; }
@media (max-width: 900px) {
  .auth-shell { grid-template-columns: 1fr; }
  .visual-side { display: none; }
  .form-side { padding: 24px; }
  .mobile-brand { width: min(430px,100%); margin-bottom: 34px; display: flex; align-items: center; gap: 8px; font-family: "Barlow Condensed"; font-size: 1.25rem; font-weight: 700; }
  .mobile-brand :deep(svg) { color: var(--primary); }
}
</style>
