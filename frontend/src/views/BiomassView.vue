<template>
  <div class="biomass-page" v-loading="store.biomass.loading">
    <div class="page-header">
      <h3>生物质热电联产</h3>
      <el-divider />
    </div>

    <el-row :gutter="20">
      <el-col :span="6" v-for="card in statCards" :key="card.label">
        <el-card shadow="hover" :class="['stat-card', card.color]">
          <div class="stat-value">{{ card.value }}</div>
          <div class="stat-label">{{ card.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top:20px">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header><span>CHP 系统能流分析</span></template>
          <el-row :gutter="20">
            <el-col :span="6" v-for="item in chpFlowCards" :key="item.label">
              <el-card shadow="hover" :class="['flow-card', item.color]">
                <div class="flow-icon">{{ item.icon }}</div>
                <div class="flow-value">{{ item.value }}</div>
                <div class="flow-label">{{ item.label }}</div>
                <div class="flow-detail">{{ item.detail }}</div>
              </el-card>
            </el-col>
          </el-row>
          <el-row style="margin-top:20px">
            <el-col :span="24">
              <div ref="sankeyChartRef" style="height: 280px;"></div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>

    <el-row style="margin-top:20px">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header><span>沼气分析</span></template>
          <el-table :data="biogasTable" border stripe>
            <el-table-column prop="label" label="指标" width="200" />
            <el-table-column prop="value" label="数值" />
            <el-table-column prop="unit" label="单位" width="120" />
          </el-table>
          <el-empty v-if="!biogasTable.length" description="暂无数据" />
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
  const d = store.biomass.chpAnalysis
  return [
    { label: 'CHP 发电出力 (kW)', value: d?.project?.capacity?.electric_power_kw?.toLocaleString() ?? '--', color: 'green' },
    { label: '供热出力 (kW)', value: d?.project?.capacity?.thermal_power_kw?.toLocaleString() ?? '--', color: 'orange' },
    { label: '综合效率', value: d?.project?.capacity?.total_efficiency ? `${d.project.capacity.total_efficiency}%` : '--', color: 'blue' },
    { label: '碳减排量 (tCO₂)', value: d?.carbon_benefit?.annual_carbon_reduction_tco2?.toLocaleString() ?? '--', color: 'green' },
  ]
})

const chpFlowCards = computed(() => {
  const d = store.biomass.chpAnalysis
  const cap = d?.project?.capacity || {}
  const elec = cap.electric_power_kw || 0
  const therm = cap.thermal_power_kw || 0
  const eff = (cap.total_efficiency || 100) / 100
  const totalOutput = elec + therm
  const fuelInput = eff > 0 ? Math.round(totalOutput / eff) : totalOutput
  const heatLoss = fuelInput - totalOutput
  const elecEff = fuelInput > 0 ? ((elec / fuelInput) * 100).toFixed(1) : 0
  const thermEff = fuelInput > 0 ? ((therm / fuelInput) * 100).toFixed(1) : 0
  const lossPct = fuelInput > 0 ? ((heatLoss / fuelInput) * 100).toFixed(1) : 0
  return [
    { label: '燃料输入', value: `${fuelInput.toLocaleString()} kW`, icon: '🔥', color: 'orange', detail: `生物质 ${d?.project?.feedstock ?? '秸秆'}` },
    { label: '发电输出', value: `${elec.toLocaleString()} kW`, icon: '⚡', color: 'green', detail: `发电效率 ${elecEff}%` },
    { label: '供热输出', value: `${therm.toLocaleString()} kW`, icon: '♨️', color: 'blue', detail: `供热效率 ${thermEff}%` },
    { label: '热损失', value: `${heatLoss.toLocaleString()} kW`, icon: '🌡️', color: 'red', detail: `损失率 ${lossPct}%` },
  ]
})

const biogasTable = computed(() => {
  const d = store.biomass.biogasAnalysis
  if (!d) return []
  return [
    { label: '项目名称', value: d.project?.name ?? '--', unit: '' },
    { label: '技术工艺', value: d.project?.technology ?? '--', unit: '' },
    { label: '日处理量', value: d.project?.capacity?.daily_feedstock_ton?.toLocaleString() ?? '--', unit: '吨/天' },
    { label: '日产沼气', value: d.project?.capacity?.daily_biogas_production_nm3?.toLocaleString() ?? '--', unit: 'Nm³/天' },
    { label: '甲烷含量', value: d.project?.capacity?.methane_content ?? '--', unit: '%' },
    { label: 'CHP日发电量', value: d.biogas_utilization?.chp_electricity_kwh_per_day?.toLocaleString() ?? '--', unit: 'kWh/天' },
    { label: 'CHP日供热量', value: d.biogas_utilization?.chp_heat_gj_per_day?.toLocaleString() ?? '--', unit: 'GJ/天' },
    { label: '日产生物甲烷', value: d.biogas_utilization?.biogas_upgrading?.biomethane_nm3_per_day?.toLocaleString() ?? '--', unit: 'Nm³/天' },
    { label: '沼渣日产量', value: d.digestate?.daily_production_ton?.toLocaleString() ?? '--', unit: '吨/天' },
    { label: '总投资', value: d.economic?.total_investment_yuan ? (d.economic.total_investment_yuan / 10000).toLocaleString() : '--', unit: '万元' },
    { label: '年收入', value: d.economic?.annual_revenue?.total_yuan ? (d.economic.annual_revenue.total_yuan / 10000).toLocaleString() : '--', unit: '万元/年' },
    { label: 'IRR', value: d.economic?.irr_percent ? `${d.economic.irr_percent}%` : '--', unit: '' },
    { label: '年碳减排', value: d.carbon_benefit?.total_carbon_reduction_tco2e_per_year?.toLocaleString() ?? '--', unit: 'tCO₂e/年' },
  ]
})

const sankeyChartRef = ref(null)
let sankeyChart

function initSankeyChart() {
  if (!sankeyChartRef.value) return
  sankeyChart = echarts.init(sankeyChartRef.value)
  const d = store.biomass.chpAnalysis
  const cap = d?.project?.capacity || {}
  const elec = cap.electric_power_kw || 0
  const therm = cap.thermal_power_kw || 0
  const eff = (cap.total_efficiency || 100) / 100
  const totalOutput = elec + therm
  const fuel = eff > 0 ? Math.round(totalOutput / eff) : totalOutput
  const loss = fuel - totalOutput
  sankeyChart.setOption({
    tooltip: { trigger: 'item', triggerOn: 'mousemove' },
    series: [{
      type: 'sankey',
      layout: 'none',
      emphasis: { focus: 'adjacency' },
      nodeAlign: 'left',
      data: [
        { name: '燃料输入' },
        { name: '发电' },
        { name: '供热' },
        { name: '热损失' },
      ],
      links: [
        { source: '燃料输入', target: '发电', value: elec },
        { source: '燃料输入', target: '供热', value: therm },
        { source: '燃料输入', target: '热损失', value: loss },
      ],
      label: { show: true, formatter: '{b}\n{c} kW' },
      lineStyle: { color: 'gradient', curveness: 0.5 },
      itemStyle: {
        color: '#409EFF',
        borderColor: '#409EFF',
      },
    }],
  })
}

function resizeAll() {
  sankeyChart?.resize()
}

onMounted(async () => {
  await nextTick()
  initSankeyChart()
  window.addEventListener('resize', resizeAll)
  await store.fetchCHPAnalysis()
  await store.fetchBiogasAnalysis()
  initSankeyChart()
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeAll)
  sankeyChart?.dispose()
})
</script>

<style scoped>
.biomass-page { padding: 4px; }
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
.flow-card { text-align: center; }
.flow-icon { font-size: 32px; margin-bottom: 8px; }
.flow-value { font-size: 22px; font-weight: bold; }
.flow-label { font-size: 14px; color: #303133; margin-top: 4px; }
.flow-detail { font-size: 12px; color: #909399; margin-top: 4px; }
</style>