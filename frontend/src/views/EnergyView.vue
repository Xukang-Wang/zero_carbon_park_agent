<template>
  <div class="energy-page" v-loading="store.energy.loading">
    <div class="page-header">
      <h3>能源调度管理</h3>
      <el-divider />
    </div>

    <!-- 上层：4 个统计卡片 -->
    <el-row :gutter="20">
      <el-col :span="6" v-for="card in statCards" :key="card.label">
        <el-card shadow="hover" :class="['stat-card', card.color]">
          <div class="stat-value">{{ card.value }}</div>
          <div class="stat-label">{{ card.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 中层：预测曲线 -->
    <el-row :gutter="20" style="margin-top:20px">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>光伏出力预测 (24h)</span></template>
          <div ref="pvChartRef" style="height: 320px;"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>风电出力预测 (24h)</span></template>
          <div ref="windChartRef" style="height: 320px;"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 下层：绿电溯源 -->
    <el-row style="margin-top:20px">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header><span>绿电溯源</span></template>
          <el-row :gutter="16" style="margin-bottom:16px">
            <el-col :span="6">
              <el-input v-model="traceEntityId" placeholder="输入实体ID" clearable />
            </el-col>
            <el-col :span="4">
              <el-button type="primary" @click="handleTrace" :loading="store.energy.loading">
                开始溯源
              </el-button>
            </el-col>
          </el-row>
          <el-table :data="traceTableData" border stripe v-if="traceTableData.length">
            <el-table-column prop="direction" label="方向" width="80" />
            <el-table-column prop="name" label="名称" />
            <el-table-column prop="type" label="类型">
              <template #default="{ row }">
                <el-tag :type="row.type === '光伏' ? 'success' : row.type === '风电' ? 'primary' : 'info'">
                  {{ row.type }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="power_kw" label="出力(kW)" />
            <el-table-column prop="ratio" label="占比" />
            <el-table-column prop="carbon_factor" label="碳排放因子" />
            <el-table-column prop="timestamp" label="时间" />
          </el-table>
          <el-empty v-else description="输入实体ID后点击溯源" />
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

const statCards = computed(() => {
  const ds = store.energy.dispatchStatus
  const pvPower = ds?.pv_station?.current_power_kw
  const windPower = 0
  const renewableRatio = ds?.total_load?.renewable_ratio
  const totalLoad = ds?.total_load?.current_power_kw
  const carbonReduction = (renewableRatio != null && totalLoad != null)
    ? (renewableRatio * totalLoad * 0.581 / 1000)
    : null
  return [
    { label: '光伏出力 (kW)', value: pvPower?.toLocaleString() ?? '--', color: 'green' },
    { label: '风电出力 (kW)', value: windPower?.toLocaleString() ?? '--', color: 'blue' },
    { label: '可再生能源占比', value: renewableRatio != null ? `${(renewableRatio * 100).toFixed(1)}%` : '--', color: 'green' },
    { label: '碳减排量 (tCO₂)', value: carbonReduction?.toFixed(1) ?? '--', color: 'purple' },
  ]
})

const traceEntityId = ref('')
const traceTableData = ref([])

async function handleTrace() {
  if (!traceEntityId.value) return
  await store.traceGreenPower(traceEntityId.value)
  const data = store.energy.greenPowerTrace
  if (!data) { traceTableData.value = []; return }
  const upstream = (data.upstream_trace || []).map(item => ({ ...item, direction: '上游' }))
  const downstream = (data.downstream_trace || []).map(item => ({ ...item, direction: '下游' }))
  traceTableData.value = [...upstream, ...downstream]
}

// 图表
const pvChartRef = ref(null)
const windChartRef = ref(null)
let pvChart, windChart

function makeChartOption(forecastData, colorRgb) {
  const hours = Array.from({ length: 24 }, (_, i) => `${i}:00`)
  const seriesData = (forecastData || []).map(f => f.power_kw ?? 0)
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 50, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: hours },
    yAxis: { type: 'value', name: 'kW' },
    series: [{
      type: 'line', smooth: true, data: seriesData,
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: `rgba(${colorRgb},0.4)` },
        { offset: 1, color: `rgba(${colorRgb},0.05)` },
      ])},
      itemStyle: { color: `rgb(${colorRgb})` },
      lineStyle: { color: `rgb(${colorRgb})`, width: 2 },
    }],
  }
}

function initPVChart() {
  if (!pvChartRef.value) return
  pvChart = echarts.init(pvChartRef.value)
  pvChart.setOption(makeChartOption([], '103,194,58'))
}

function initWindChart() {
  if (!windChartRef.value) return
  windChart = echarts.init(windChartRef.value)
  windChart.setOption(makeChartOption([], '64,158,255'))
}

function updatePVChart(data) {
  pvChart?.setOption(makeChartOption(data, '103,194,58'))
}

function updateWindChart(data) {
  windChart?.setOption(makeChartOption(data, '64,158,255'))
}

function resizeAll() {
  pvChart?.resize()
  windChart?.resize()
}

onMounted(async () => {
  await nextTick()
  initPVChart()
  initWindChart()
  window.addEventListener('resize', resizeAll)
  await store.fetchEnergyDispatch()
  await store.fetchPowerForecast('pv')
  updatePVChart(store.energy.pvForecast?.forecast)
  await store.fetchPowerForecast('wind')
  updateWindChart(store.energy.windForecast?.forecast)
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeAll)
  pvChart?.dispose()
  windChart?.dispose()
})
</script>

<style scoped>
.energy-page { padding: 4px; }
.page-header h3 { margin: 0; font-size: 18px; color: #303133; }
.stat-card {
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  border-top: 3px solid transparent;
  background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
}
.stat-card:hover {
  transform: translateY(-4px) scale(1.02);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.12) !important;
}
.stat-value { font-size: clamp(20px, 2.5vw, 28px); font-weight: bold; color: #303133; }
.stat-label { font-size: 14px; color: #909399; margin-top: 8px; }
.green { border-top-color: #67C23A; }
.blue { border-top-color: #409EFF; }
.orange { border-top-color: #E6A23C; }
.purple { border-top-color: #9C27B0; }
.red { border-top-color: #F56C6C; }
</style>