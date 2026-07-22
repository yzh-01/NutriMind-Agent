<template>
  <article class="metric-chart surface-soft">
    <header>
      <div><span>Epoch trend</span><h3>{{ title }}</h3></div>
      <ul class="chart-legend" aria-label="图表图例">
        <li v-for="item in chartSeries" :key="item.key" :class="item.tone">
          <i :class="item.dash" />{{ item.label }}<strong>{{ formatValue(item.latest) }}</strong>
        </li>
      </ul>
    </header>

    <div v-if="!hasData" class="chart-empty" role="status">暂无可绘制的训练指标</div>
    <svg
      v-else
      class="chart-svg"
      viewBox="0 0 640 250"
      role="img"
      :aria-label="`${title}，共 ${rows.length} 个训练轮次数据点`"
    >
      <g class="grid-lines">
        <template v-for="line in gridLines" :key="line.y">
          <line x1="54" :y1="line.y" x2="620" :y2="line.y" />
          <text x="46" :y="line.y + 4" text-anchor="end">{{ formatAxis(line.value) }}</text>
        </template>
      </g>
      <line class="axis-line" x1="54" y1="220" x2="620" y2="220" />
      <text class="axis-label" x="54" y="241">Epoch {{ firstEpoch }}</text>
      <text class="axis-label" x="620" y="241" text-anchor="end">Epoch {{ lastEpoch }}</text>
      <g v-for="item in chartSeries" :key="item.key" :class="['series', item.tone]">
        <polyline :class="item.dash" :points="item.points" />
        <circle v-if="item.lastPoint" :cx="item.lastPoint.x" :cy="item.lastPoint.y" r="4" />
      </g>
    </svg>

    <details v-if="hasData" class="raw-data">
      <summary>查看精确指标数据</summary>
      <div>
        <table>
          <thead><tr><th>Epoch</th><th v-for="item in series" :key="item.key">{{ item.label }}</th></tr></thead>
          <tbody>
            <tr v-for="row in rows" :key="row.epoch">
              <td>{{ row.epoch }}</td><td v-for="item in series" :key="item.key">{{ formatValue(row[item.key]) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </details>
  </article>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: { type: String, required: true },
  rows: { type: Array, default: () => [] },
  series: { type: Array, default: () => [] },
})

const plot = { left: 54, right: 620, top: 16, bottom: 220 }
const values = computed(() => props.rows.flatMap((row) => props.series
  .map((item) => Number(row[item.key]))
  .filter(Number.isFinite)))
const hasData = computed(() => values.value.length > 0)
const range = computed(() => {
  if (!hasData.value) return { min: 0, max: 1 }
  const min = Math.min(...values.value)
  const max = Math.max(...values.value)
  if (min === max) return { min: min - 1, max: max + 1 }
  const padding = (max - min) * .08
  return { min: Math.max(0, min - padding), max: max + padding }
})
const firstEpoch = computed(() => props.rows[0]?.epoch ?? '--')
const lastEpoch = computed(() => props.rows.at(-1)?.epoch ?? '--')

function pointFor(value, index) {
  const width = plot.right - plot.left
  const height = plot.bottom - plot.top
  const x = props.rows.length <= 1 ? plot.left + width / 2 : plot.left + width * index / (props.rows.length - 1)
  const y = plot.bottom - (value - range.value.min) / (range.value.max - range.value.min) * height
  return { x, y }
}

const chartSeries = computed(() => props.series.map((item) => {
  const points = props.rows.map((row, index) => {
    const value = Number(row[item.key])
    return Number.isFinite(value) ? pointFor(value, index) : null
  }).filter(Boolean)
  const latestRow = [...props.rows].reverse().find((row) => Number.isFinite(Number(row[item.key])))
  return {
    ...item,
    points: points.map((point) => `${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(' '),
    lastPoint: points.at(-1) || null,
    latest: latestRow ? Number(latestRow[item.key]) : null,
  }
}))

const gridLines = computed(() => Array.from({ length: 5 }, (_, index) => {
  const ratio = index / 4
  return {
    y: plot.top + (plot.bottom - plot.top) * ratio,
    value: range.value.max - (range.value.max - range.value.min) * ratio,
  }
}))

function formatValue(value) {
  return Number.isFinite(Number(value)) ? Number(value).toFixed(4) : '--'
}

function formatAxis(value) {
  if (!Number.isFinite(value)) return '--'
  return Math.abs(value) >= 10 ? value.toFixed(1) : value.toFixed(2)
}
</script>

<style lang="scss" scoped>
.metric-chart { padding: 18px; border: 1px solid var(--border); border-radius: 13px; background: var(--canvas-soft); }
.metric-chart > header { display: flex; align-items: flex-start; justify-content: space-between; gap: 18px; }
.metric-chart header > div { display: grid; gap: 3px; }
.metric-chart header span { color: var(--primary); font-size: .62rem; font-weight: 600; text-transform: uppercase; }
.metric-chart h3 { margin: 0; color: var(--text); font-family: "Barlow Condensed"; font-size: 1.3rem; }
.chart-legend { margin: 0; padding: 0; display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 7px 12px; list-style: none; }
.chart-legend li { display: grid; grid-template-columns: 18px auto auto; align-items: center; gap: 5px; color: var(--muted); font-size: .58rem; }
.chart-legend i { width: 18px; height: 0; border-top: 2px solid currentColor; }
.chart-legend i.dashed { border-top-style: dashed; }
.chart-legend i.dotted { border-top-style: dotted; }
.chart-legend strong { color: var(--text-secondary); font-size: .58rem; font-variant-numeric: tabular-nums; }
.green { color: var(--primary) !important; }
.orange { color: var(--accent) !important; }
.blue { color: #71b7ff !important; }
.red { color: #ff938d !important; }
.chart-svg { width: 100%; margin-top: 18px; display: block; overflow: visible; }
.grid-lines line { stroke: rgba(255,255,255,.07); stroke-width: 1; }
.grid-lines text, .axis-label { fill: var(--muted); font-size: 10px; font-family: "Barlow"; }
.axis-line { stroke: var(--border-strong); stroke-width: 1; }
.series polyline { fill: none; stroke: currentColor; stroke-width: 2.4; stroke-linecap: round; stroke-linejoin: round; vector-effect: non-scaling-stroke; }
.series polyline.dashed { stroke-dasharray: 8 5; }
.series polyline.dotted { stroke-dasharray: 2 5; }
.series circle { fill: var(--surface); stroke: currentColor; stroke-width: 2.5; vector-effect: non-scaling-stroke; }
.chart-empty { min-height: 230px; display: grid; place-content: center; color: var(--muted); font-size: .72rem; }
.raw-data { margin-top: 8px; color: var(--muted); font-size: .65rem; }
.raw-data summary { min-height: 40px; display: flex; align-items: center; cursor: pointer; }
.raw-data > div { max-height: 260px; overflow: auto; border: 1px solid var(--border); border-radius: 9px; }
.raw-data table { width: 100%; border-collapse: collapse; }
.raw-data th, .raw-data td { padding: 8px 9px; border-bottom: 1px solid var(--border); text-align: right; white-space: nowrap; }
.raw-data th:first-child, .raw-data td:first-child { text-align: left; }
.raw-data th { position: sticky; top: 0; color: var(--text-secondary); background: var(--surface-raised); }
.raw-data td { color: var(--muted); font-variant-numeric: tabular-nums; }
@media (max-width: 620px) {
  .metric-chart { padding: 14px; }
  .metric-chart > header { flex-direction: column; }
  .chart-legend { justify-content: flex-start; }
  .chart-svg { margin-top: 12px; }
}
</style>
