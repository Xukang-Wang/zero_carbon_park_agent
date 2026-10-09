<template><div ref="el" class="operations-chart" role="img" :aria-label="label" /></template>
<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as echarts from 'echarts'
const props = defineProps({ option: Object, label: { type: String, default: '园区分析图表' } })
const el = ref(null)
let chart, observer
onMounted(() => {
  chart = echarts.init(el.value)
  chart.setOption(props.option || {})
  observer = new ResizeObserver(() => chart?.resize())
  observer.observe(el.value)
})
watch(() => props.option, value => chart?.setOption(value || {}, true), { deep: true })
onBeforeUnmount(() => { observer?.disconnect(); chart?.dispose() })
</script>
<style scoped>.operations-chart { width: 100%; height: 290px; min-width: 0; }</style>
