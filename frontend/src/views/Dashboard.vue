<template>
  <div class="dashboard">
    <!-- 概览卡片 - 源网荷储核心指标 -->
    <el-row :gutter="16">
      <el-col :span="3" v-for="card in statCards" :key="card.label">
        <el-card shadow="hover" :class="['stat-card', card.color]">
          <div class="stat-value">
            <el-skeleton :loading="store.park.loading && !store.park.snapshot" animated :rows="0">
              <template #default>{{ card.value }}</template>
              <template #template><div style="height:28px;width:60%;margin:0 auto;background:#eee;border-radius:4px" /></template>
            </el-skeleton>
          </div>
          <div class="stat-label">{{ card.label }}</div>
          <div class="stat-sub" v-if="card.sub">{{ card.sub }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 源网荷储功率流 -->
    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="16">
        <el-card shadow="hover">
          <template #header>
            <span>源网荷储功率流 (24h)</span>
            <el-tag size="small" type="success" style="margin-left:8px" v-if="powerBalance">平衡: {{ powerBalance }}</el-tag>
          </template>
          <div :ref="powerFlowChart.container" style="height: 380px;"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header><span>储能SOC</span></template>
          <div :ref="socGaugeChart.container" style="height: 180px;"></div>
          <el-descriptions :column="1" size="small" border style="margin-top:8px">
            <el-descriptions-item label="健康度(SOH)">{{ parkSnapshot?.storage?.soh ?? '--' }}%</el-descriptions-item>
            <el-descriptions-item label="循环次数">{{ parkSnapshot?.storage?.cycle_count ?? '--' }}</el-descriptions-item>
            <el-descriptions-item label="温度">{{ parkSnapshot?.storage?.temp_c ?? '--' }}°C</el-descriptions-item>
            <el-descriptions-item label="可用能量">{{ parkSnapshot?.storage?.available_energy_kwh ?? '--' }} kWh</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>

    <!-- 负荷与碳排放 -->
    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>负荷分布</span></template>
          <div :ref="loadChart.container" style="height: 280px;"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>碳排放拆解 (Scope 1/2/3)</span></template>
          <div :ref="carbonChart.container" style="height: 280px;"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 告警与调度策略 -->
    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <span>实时告警</span>
            <el-button size="small" type="primary" link @click="refreshAlerts" style="float:right">刷新</el-button>
          </template>
          <el-timeline v-if="alertItems.length">
            <el-timeline-item
              v-for="a in alertItems" :key="a.id"
              :timestamp="a.time"
              :color="a.level === 'critical' ? '#F56C6C' : a.level === 'warning' ? '#E6A23C' : '#409EFF'"
            >[{{ a.node_type }}] {{ a.message }}</el-timeline-item>
          </el-timeline>
          <el-empty v-else description="系统运行正常，无告警" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <span>调度策略优化</span>
            <el-select v-model="dispatchStrategy" size="small" style="width:130px;float:right;margin-left:8px" @change="runDispatch">
              <el-option label="经济最优" value="economic" />
              <el-option label="低碳优先" value="low_carbon" />
              <el-option label="平衡模式" value="balanced" />
              <el-option label="削峰填谷" value="peak_shaving" />
              <el-option label="价差套利" value="price_arbitrage" />
            </el-select>
            <el-button size="small" type="primary" @click="runDispatch" style="float:right">执行优化</el-button>
          </template>
          <div v-if="dispatchResult" class="dispatch-summary">
            <el-row :gutter="12">
              <el-col :span="8" v-for="item in dispatchMetrics" :key="item.label">
                <div class="metric-item">
                  <div class="metric-value" :style="{color: item.color}">{{ item.value }}</div>
                  <div class="metric-label">{{ item.label }}</div>
                </div>
              </el-col>
            </el-row>
          </div>
          <el-empty v-else description='点击"执行优化"生成调度方案' />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, watch } from 'vue'
import * as echarts from 'echarts'
import { useApiStore } from '../stores/api'
import { useChart } from '../composables/useChart'

const store = useApiStore()
const dispatchStrategy = ref('balanced')

const parkSnapshot = computed(() => store.park.snapshot)
const dispatchResult = computed(() => store.park.dispatchResult)

// 概览卡片
const statCards = computed(() => {
  const snap = parkSnapshot.value
  return [
    { label: '光伏 (kW)', value: snap?.generation?.pv?.current_power_kw?.toFixed(0) ?? '--', color: 'green', sub: snap ? `辐照 ${snap.generation.pv.irradiance_wm2}W/m²` : '' },
    { label: '风电 (kW)', value: snap?.generation?.wind?.current_power_kw?.toFixed(0) ?? '--', color: 'cyan', sub: snap ? `风速 ${snap.generation.wind.wind_speed_ms}m/s` : '' },
    { label: '负荷 (kW)', value: snap?.loads?.total_power_kw?.toFixed(0) ?? '--', color: 'blue', sub: snap ? `DR ${snap.loads.demand_response_capacity_kw}kW` : '' },
    { label: '储能 SOC (%)', value: snap?.storage?.current_soc?.toFixed(1) ?? '--', color: 'purple', sub: snap ? `SOH ${snap.storage.soh}%` : '' },
    { label: '电网 (kW)', value: snap?.grid?.current_power_kw?.toFixed(0) ?? '--', color: 'orange', sub: snap ? (snap.grid.is_importing ? '购电中' : '售电中') : '' },
    { label: '可再生占比 (%)', value: snap?.carbon?.renewable_ratio?.toFixed(1) ?? '--', color: 'green' },
    { label: '碳排放 (tCO₂/h)', value: snap?.grid?.carbon_emission_tco2_per_h?.toFixed(4) ?? '--', color: 'orange' },
    { label: '系统状态', value: snap?.park?.status === 'running' ? '正常运行' : '--', color: 'green', sub: snap?.alerts?.system_status ?? '' },
  ]
})

const alertItems = computed(() => {
  const alerts = store.park.alerts?.active_alerts || []
  return alerts.map((a, i) => ({ id: i, time: a.timestamp?.slice(11, 19) || '', level: a.level, node_type: a.node_type, message: a.message }))
})

const powerBalance = computed(() => {
  const snap = parkSnapshot.value
  if (!snap) return null
  return `${snap.micro_grid?.power_balance?.toFixed(0) ?? 0} kW`
})

const dispatchMetrics = computed(() => {
  const r = dispatchResult.value?.summary
  if (!r) return []
  return [
    { label: '净成本', value: `¥${r.net_cost_yuan?.toFixed(0) ?? 0}`, color: '#F56C6C' },
    { label: '可再生比', value: `${r.renewable_ratio ?? 0}%`, color: '#67C23A' },
    { label: '碳排放', value: `${r.total_carbon_emission_tco2?.toFixed(2) ?? 0}t`, color: '#E6A23C' },
    { label: '削峰次数', value: `${r.peak_shaving_times ?? 0}次`, color: '#409EFF' },
    { label: '填谷次数', value: `${r.valley_filling_times ?? 0}次`, color: '#67C23A' },
    { label: '失负荷', value: `${r.loss_of_load_times ?? 0}次`, color: '#909399' },
  ]
})

// 功率流图
const powerFlowChart = useChart(() => {
  const trend = store.park.hourlyTrend
  const hours = trend.length ? trend.map(t => t.time) : Array.from({length: 24}, (_, i) => `${i}:00`)
  const pv = trend.length ? trend.map(t => t.pv_power_kw) : Array(24).fill(0)
  const wind = trend.length ? trend.map(t => t.wind_power_kw) : Array(24).fill(0)
  const load = trend.length ? trend.map(t => t.load_power_kw) : Array(24).fill(0)
  const storage = trend.length ? trend.map(t => t.storage_power_kw) : Array(24).fill(0)
  const grid = trend.length ? trend.map(t => t.grid_power_kw) : Array(24).fill(0)
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['光伏', '风电', '负荷', '储能', '电网'] },
    xAxis: { type: 'category', data: hours },
    yAxis: { type: 'value', name: 'kW' },
    series: [
      { name: '光伏', type: 'line', data: pv, smooth: true, areaStyle: { opacity: 0.15 }, color: '#67C23A', lineStyle: { width: 2 } },
      { name: '风电', type: 'line', data: wind, smooth: true, areaStyle: { opacity: 0.1 }, color: '#00BCD4', lineStyle: { width: 2 } },
      { name: '负荷', type: 'line', data: load, smooth: true, color: '#409EFF', lineStyle: { width: 2.5 } },
      { name: '储能', type: 'line', data: storage, smooth: true, color: '#9C27B0', lineStyle: { width: 1.5, type: 'dashed' } },
      { name: '电网', type: 'line', data: grid, smooth: true, color: '#E6A23C', lineStyle: { width: 1.5, type: 'dashed' } },
    ],
  }
})

// SOC仪表盘
const socGaugeChart = useChart(() => {
  const soc = parkSnapshot.value?.storage?.current_soc ?? 60
  return {
    series: [{
      type: 'gauge',
      center: ['50%', '55%'],
      radius: '85%',
      startAngle: 210, endAngle: -30,
      min: 0, max: 100,
      splitNumber: 5,
      axisLine: { lineStyle: { width: 16, color: [[0.2, '#F56C6C'], [0.5, '#E6A23C'], [0.8, '#409EFF'], [1, '#67C23A']] } },
      axisTick: { show: false },
      axisLabel: { distance: 18, fontSize: 11 },
      pointer: { length: '60%', width: 6 },
      detail: { valueAnimation: true, formatter: '{value}%', fontSize: 20, offsetCenter: [0, '78%'] },
      data: [{ value: soc, name: 'SOC' }],
    }],
  }
})

// 负荷分布图
const loadChart = useChart(() => {
  const breakdown = parkSnapshot.value?.loads?.breakdown || []
  const names = breakdown.map(l => l.name)
  const values = breakdown.map(l => l.current_power_kw)
  const flexRatio = { fixed: 0, shiftable: 0.5, flexible: 0.3 }
  const flex = breakdown.map(l => Math.round((l.current_power_kw || 0) * (flexRatio[l.flexibility] || 0)))
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['实际功率', '可调容量'] },
    xAxis: { type: 'category', data: names, axisLabel: { rotate: 30 } },
    yAxis: { type: 'value', name: 'kW' },
    series: [
      { name: '实际功率', type: 'bar', data: values, color: '#409EFF' },
      { name: '可调容量', type: 'bar', data: flex, color: '#67C23A' },
    ],
  }
})

// 碳排放图
const carbonChart = useChart(() => {
  const carbon = parkSnapshot.value?.carbon?.scope_breakdown
  return {
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['45%', '70%'],
      label: { formatter: '{b}\n{d}%' },
      data: [
        { value: carbon?.scope_1?.emission_tco2 ?? 0, name: 'Scope1 直接排放', itemStyle: { color: '#F56C6C' } },
        { value: carbon?.scope_2?.emission_tco2 ?? 0, name: 'Scope2 外购电力', itemStyle: { color: '#E6A23C' } },
        { value: carbon?.scope_3?.emission_tco2 ?? 0, name: 'Scope3 其他间接', itemStyle: { color: '#909399' } },
        { value: carbon?.carbon_offset_tco2 ?? 0, name: '碳抵消', itemStyle: { color: '#67C23A' } },
      ],
    }],
  }
})

async function runDispatch() {
  await store.optimizeDispatch(dispatchStrategy.value)
}

async function refreshAlerts() {
  await store.fetchParkAlerts()
}

onMounted(async () => {
  await Promise.all([
    store.fetchParkSnapshot(),
    store.fetchHourlyTrend(24),
    store.fetchParkAlerts(),
  ])
  powerFlowChart.update()
  socGaugeChart.update()
  loadChart.update()
  carbonChart.update()
})

watch(() => store.park.snapshot, () => {
  socGaugeChart.update()
  loadChart.update()
  carbonChart.update()
})

watch(() => store.park.hourlyTrend, () => {
  powerFlowChart.update()
})
</script>

<style scoped>
.dashboard { padding: 4px; }
.stat-card {
  text-align: center; cursor: pointer;
  transition: all 0.3s ease;
  border-top: 3px solid transparent;
  background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
}
.stat-card:hover { transform: translateY(-4px); box-shadow: 0 8px 25px rgba(0,0,0,0.12) !important; }
.stat-value { font-size: clamp(20px, 2.5vw, 28px); font-weight: bold; min-height: 36px; color: #303133; }
.stat-label { font-size: 13px; color: #909399; margin-top: 4px; }
.stat-sub { font-size: 11px; color: #c0c4cc; margin-top: 2px; }
.green { border-top-color: #67C23A; }
.blue { border-top-color: #409EFF; }
.orange { border-top-color: #E6A23C; }
.purple { border-top-color: #9C27B0; }
.cyan { border-top-color: #00BCD4; }
.dispatch-summary { padding: 8px 0; }
.metric-item { text-align: center; padding: 8px 0; }
.metric-value { font-size: 22px; font-weight: bold; }
.metric-label { font-size: 12px; color: #909399; margin-top: 2px; }
</style>