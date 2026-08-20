<template>
  <div class="carbon-tracker">
    <el-row :gutter="20">
      <el-col :span="6" v-for="item in carbonMetrics" :key="item.label">
        <el-card shadow="hover" class="carbon-card">
          <div class="carbon-value" :style="{ color: item.color }">
            <el-skeleton :loading="store.carbon.loading" animated :rows="0">
              <template #default>{{ item.value }}</template>
              <template #template><div style="height:28px;width:60%;margin:0 auto;background:#eee;border-radius:4px" /></template>
            </el-skeleton>
          </div>
          <div class="carbon-label">{{ item.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top:20px">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>碳排放趋势 (近7天)</span></template>
          <div v-if="!store.carbon.loading" ref="trendChartRef" style="height: 350px;"></div>
          <el-skeleton v-else :rows="10" animated style="padding:20px" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>碳足迹构成</span></template>
          <div v-if="!store.carbon.loading" ref="pieChartRef" style="height: 350px;"></div>
          <el-skeleton v-else :rows="10" animated style="padding:20px" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, nextTick } from 'vue'
import * as echarts from 'echarts'
import { useApiStore } from '../stores/api'

const store = useApiStore()

const carbonMetrics = computed(() => {
  const f = store.carbon.footprint ?? {}
  return [
    { label: '直接排放 (tCO₂/h)', value: f.direct_emission_tco2_per_h ?? '--', color: '#F56C6C' },
    { label: '间接排放 (tCO₂/h)', value: f.indirect_emission_tco2_per_h ?? '--', color: '#E6A23C' },
    { label: '碳抵消 (tCO₂/h)', value: f.carbon_offset_tco2_per_h ?? '--', color: '#67C23A' },
    { label: '净排放 (tCO₂/h)', value: f.net_emission_tco2_per_h ?? '--', color: '#409EFF' },
  ]
})

const trendChartRef = ref(null)
const pieChartRef = ref(null)
let trendChart, pieChart

function initTrendChart() {
  if (!trendChartRef.value) return
  trendChart = echarts.init(trendChartRef.value)
  const trend = store.carbon.trend
  const days = trend.length ? trend.map(t => t.date?.slice(5) || '--') : ['8/1', '8/2', '8/3', '8/4', '8/5', '8/6', '8/7']
  const net = trend.length ? trend.map(t => t.net_emission_tco2 ?? 0) : [35, 32, 38, 40, 36, 34, 33]
  const direct = trend.length ? trend.map(t => t.direct_emission_tco2 ?? 0) : [12, 11, 13, 14, 12, 12, 11]
  const offset = trend.length ? trend.map(t => Math.round((t.direct_emission_tco2 ?? 0) * (t.renewable_ratio ?? 0) * 10) / 10) : [23, 22, 24, 25, 23, 23, 22]
  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['净排放', '直接排放', '碳抵消'] },
    xAxis: { type: 'category', data: days },
    yAxis: { type: 'value', name: 'tCO₂/天' },
    series: [
      { name: '净排放', type: 'line', smooth: true, data: net, areaStyle: {} },
      { name: '直接排放', type: 'line', smooth: true, data: direct },
      { name: '碳抵消', type: 'line', smooth: true, data: offset, lineStyle: { type: 'dashed' } },
    ],
  })
}

function initPieChart() {
  if (!pieChartRef.value) return
  pieChart = echarts.init(pieChartRef.value)
  const f = store.carbon.footprint ?? {}
  pieChart.setOption({
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: '60%',
      data: [
        { value: f.direct_emission_tco2_per_h || 0.5, name: '直接排放', itemStyle: { color: '#F56C6C' } },
        { value: f.indirect_emission_tco2_per_h || 2.5, name: '间接排放', itemStyle: { color: '#E6A23C' } },
        { value: f.carbon_offset_tco2_per_h || 1.0, name: '碳抵消', itemStyle: { color: '#67C23A' } },
      ],
    }],
  })
}

onMounted(async () => {
  await nextTick()
  await store.fetchCarbon()
  initTrendChart()
  initPieChart()
  window.addEventListener('resize', () => { trendChart?.resize(); pieChart?.resize() })
})

onUnmounted(() => {
  trendChart?.dispose()
  pieChart?.dispose()
})
</script>

<style scoped>
.carbon-card { text-align: center; }
.carbon-value { font-size: 28px; font-weight: bold; min-height: 36px; }
.carbon-label { font-size: 13px; color: #909399; margin-top: 6px; }
</style>