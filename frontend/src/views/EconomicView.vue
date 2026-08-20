<template>
  <div class="economic-page" v-loading="store.economic.loading">
    <div class="page-header">
      <h3>经济性分析</h3>
      <el-divider />
    </div>

    <el-tabs v-model="activeTab" type="border-card">
      <el-tab-pane label="光伏" name="pv">
        <el-row :gutter="20">
          <el-col :span="8" v-for="item in pvCards" :key="item.label">
            <el-card shadow="hover" :class="['econ-card', item.color]">
              <div class="econ-value">{{ item.value }}</div>
              <div class="econ-label">{{ item.label }}</div>
            </el-card>
          </el-col>
        </el-row>
        <el-row style="margin-top:20px">
          <el-col :span="24">
            <el-card shadow="hover">
              <template #header><span>光伏发电收益趋势</span></template>
              <div ref="pvChartRef" style="height: 300px;"></div>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>

      <el-tab-pane label="储能" name="storage">
        <el-row :gutter="20">
          <el-col :span="8" v-for="item in storageCards" :key="item.label">
            <el-card shadow="hover" :class="['econ-card', item.color]">
              <div class="econ-value">{{ item.value }}</div>
              <div class="econ-label">{{ item.label }}</div>
            </el-card>
          </el-col>
        </el-row>
        <el-row style="margin-top:20px">
          <el-col :span="24">
            <el-card shadow="hover">
              <template #header><span>储能收益构成</span></template>
              <div ref="storageChartRef" style="height: 300px;"></div>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>

      <el-tab-pane label="综合能源" name="comprehensive">
        <el-row :gutter="20">
          <el-col :span="8" v-for="item in compCards" :key="item.label">
            <el-card shadow="hover" :class="['econ-card', item.color]">
              <div class="econ-value">{{ item.value }}</div>
              <div class="econ-label">{{ item.label }}</div>
            </el-card>
          </el-col>
        </el-row>
        <el-row style="margin-top:20px">
          <el-col :span="24">
            <el-card shadow="hover">
              <template #header><span>综合能源投资构成</span></template>
              <div ref="compChartRef" style="height: 300px;"></div>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import { useApiStore } from '../stores/api'

const store = useApiStore()
const activeTab = ref('pv')

const pvCards = computed(() => {
  const d = store.economic.pvEconomics || {}
  return [
    { label: '总投资 (万元)', value: d.investment?.total_investment_yuan ? (d.investment.total_investment_yuan / 10000).toLocaleString() : '--', color: 'blue' },
    { label: '年收益 (万元)', value: d.revenue?.annual_total_revenue_yuan ? (d.revenue.annual_total_revenue_yuan / 10000).toLocaleString() : '--', color: 'green' },
    { label: '回收期 (年)', value: d.financial_indicators?.payback_period_years?.toFixed(1) ?? '--', color: 'orange' },
    { label: 'IRR', value: d.financial_indicators?.irr_percent ? `${d.financial_indicators.irr_percent}%` : '--', color: 'purple' },
    { label: 'NPV (万元)', value: d.financial_indicators?.npv_yuan ? (d.financial_indicators.npv_yuan / 10000).toLocaleString() : '--', color: 'green' },
    { label: 'LCOE (元/kWh)', value: d.financial_indicators?.lcoe_yuan_per_kwh?.toFixed(3) ?? '--', color: 'blue' },
  ]
})

const storageCards = computed(() => {
  const d = store.economic.storageEconomics || {}
  return [
    { label: '总投资 (万元)', value: d.investment?.total_investment_yuan ? (d.investment.total_investment_yuan / 10000).toLocaleString() : '--', color: 'blue' },
    { label: '年收益 (万元)', value: d.total_annual_revenue_yuan ? (d.total_annual_revenue_yuan / 10000).toLocaleString() : '--', color: 'green' },
    { label: '回收期 (年)', value: d.financial_indicators?.payback_period_years?.toFixed(1) ?? '--', color: 'orange' },
    { label: 'IRR', value: d.financial_indicators?.irr_percent ? `${d.financial_indicators.irr_percent}%` : '--', color: 'purple' },
    { label: 'NPV (万元)', value: d.financial_indicators?.npv_yuan ? (d.financial_indicators.npv_yuan / 10000).toLocaleString() : '--', color: 'green' },
    { label: 'LCOS (元/kWh)', value: d.financial_indicators?.lcos_yuan_per_kwh?.toFixed(3) ?? '--', color: 'blue' },
  ]
})

const compCards = computed(() => {
  const d = store.economic.comprehensive || {}
  return [
    { label: '总投资 (万元)', value: d.total_investment?.total_yuan ? (d.total_investment.total_yuan / 10000).toLocaleString() : '--', color: 'blue' },
    { label: '年收益 (万元)', value: d.annual_revenue?.total_yuan ? (d.annual_revenue.total_yuan / 10000).toLocaleString() : '--', color: 'green' },
    { label: '回收期 (年)', value: d.financial_indicators?.payback_period_years?.toFixed(1) ?? '--', color: 'orange' },
    { label: 'IRR', value: d.financial_indicators?.irr_percent ? `${d.financial_indicators.irr_percent}%` : '--', color: 'purple' },
    { label: 'NPV (万元)', value: d.financial_indicators?.npv_yuan ? (d.financial_indicators.npv_yuan / 10000).toLocaleString() : '--', color: 'green' },
    { label: '效益成本比', value: d.financial_indicators?.benefit_cost_ratio?.toFixed(2) ?? '--', color: 'blue' },
  ]
})

const pvChartRef = ref(null)
const storageChartRef = ref(null)
const compChartRef = ref(null)
let pvChart, storageChart, compChart

function initPVChart() {
  if (!pvChartRef.value) return
  pvChart = echarts.init(pvChartRef.value)
  const d = store.economic.pvEconomics
  if (!d?.investment || !d?.revenue || !d?.costs) {
    pvChart.setOption({ title: { text: '暂无数据', left: 'center', top: 'center' } })
    return
  }
  const investment = d.investment.total_investment_yuan / 10000
  const annualNet = (d.revenue.annual_total_revenue_yuan - d.costs.annual_total_cost_yuan) / 10000
  const years = ['2024', '2025', '2026', '2027', '2028', '2029', '2030', '2031', '2032', '2033']
  const annualData = [-investment, ...Array(9).fill(annualNet)]
  const cumulative = []
  let sum = 0
  annualData.forEach(v => { sum += v; cumulative.push(Number(sum.toFixed(1))) })
  pvChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['年净收益', '累计净现金流'] },
    xAxis: { type: 'category', data: years },
    yAxis: { type: 'value', name: '万元' },
    series: [
      { name: '年净收益', type: 'bar', data: annualData, color: '#67C23A' },
      { name: '累计净现金流', type: 'line', smooth: true, data: cumulative, color: '#409EFF' },
    ],
  })
}

function initStorageChart() {
  if (!storageChartRef.value) return
  storageChart = echarts.init(storageChartRef.value)
  const d = store.economic.storageEconomics
  const streams = d?.revenue_streams || []
  if (!streams.length) {
    storageChart.setOption({ title: { text: '暂无数据', left: 'center', top: 'center' } })
    return
  }
  storageChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} 万元 ({d}%)' },
    series: [{
      type: 'pie',
      radius: ['40%', '65%'],
      label: { formatter: '{b}\n{d}%' },
      data: streams.map((s, i) => ({
        name: s.name,
        value: Number((s.annual_revenue_yuan / 10000).toFixed(1)),
        itemStyle: { color: ['#67C23A', '#409EFF', '#E6A23C', '#9C27B0'][i] || '#909399' },
      })),
    }],
  })
}

function initCompChart() {
  if (!compChartRef.value) return
  compChart = echarts.init(compChartRef.value)
  const d = store.economic.comprehensive
  const inv = d?.total_investment || {}
  compChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} 万元 ({d}%)' },
    series: [{
      type: 'pie',
      radius: ['40%', '65%'],
      label: { formatter: '{b}\n{d}%' },
      data: [
        { name: '光伏系统', value: inv.pv_system_yuan ? Number((inv.pv_system_yuan / 10000).toFixed(0)) : 0, itemStyle: { color: '#67C23A' } },
        { name: '储能系统', value: inv.storage_system_yuan ? Number((inv.storage_system_yuan / 10000).toFixed(0)) : 0, itemStyle: { color: '#409EFF' } },
        { name: 'EMS平台', value: inv.ems_platform_yuan ? Number((inv.ems_platform_yuan / 10000).toFixed(0)) : 0, itemStyle: { color: '#E6A23C' } },
        { name: '碳管理平台', value: inv.carbon_platform_yuan ? Number((inv.carbon_platform_yuan / 10000).toFixed(0)) : 0, itemStyle: { color: '#9C27B0' } },
        { name: '其他', value: inv.other_yuan ? Number((inv.other_yuan / 10000).toFixed(0)) : 0, itemStyle: { color: '#909399' } },
      ].filter(d => d.value > 0),
    }],
  })
}

function resizeAll() {
  pvChart?.resize()
  storageChart?.resize()
  compChart?.resize()
}

watch(activeTab, async () => {
  await nextTick()
  if (activeTab.value === 'pv') { initPVChart() }
  else if (activeTab.value === 'storage') { initStorageChart() }
  else if (activeTab.value === 'comprehensive') { initCompChart() }
})

onMounted(async () => {
  await nextTick()
  initPVChart()
  window.addEventListener('resize', resizeAll)
  await store.fetchPVEconomics()
  await store.fetchStorageEconomics()
  await store.fetchComprehensiveEconomics()
  initPVChart()
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeAll)
  pvChart?.dispose()
  storageChart?.dispose()
  compChart?.dispose()
})
</script>

<style scoped>
.economic-page { padding: 4px; }
.page-header h3 { margin: 0; font-size: 18px; color: #303133; }
.econ-card {
  text-align: center;
  padding: 8px 0;
  cursor: pointer;
  transition: all 0.3s ease;
  border-top: 3px solid transparent;
  background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
}
.econ-card:hover {
  transform: translateY(-4px) scale(1.02);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.12) !important;
}
.econ-value { font-size: clamp(18px, 2.5vw, 24px); font-weight: bold; color: #303133; }
.econ-label { font-size: 13px; color: #909399; margin-top: 6px; }
.green { border-top-color: #67C23A; }
.blue { border-top-color: #409EFF; }
.orange { border-top-color: #E6A23C; }
.purple { border-top-color: #9C27B0; }
.red { border-top-color: #F56C6C; }
</style>