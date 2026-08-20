<template>
  <div class="carbon-asset-page" v-loading="store.carbonAsset.loading">
    <div class="page-header">
      <h3>碳资产管理</h3>
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
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>碳排放范围分布</span></template>
          <div ref="emissionChartRef" style="height: 340px;"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>排放明细</span></template>
          <el-table :data="emissionDetail" border stripe size="small">
            <el-table-column prop="category" label="排放类别" />
            <el-table-column prop="scope" label="范围">
              <template #default="{ row }">
                <el-tag :type="row.scope === 'Scope 1' ? 'danger' : row.scope === 'Scope 2' ? 'warning' : 'info'">
                  {{ row.scope }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="value_tco2" label="排放量 (tCO₂)" />
            <el-table-column prop="ratio" label="占比" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top:20px">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>碳资产组合</span></template>
          <el-row :gutter="16">
            <el-col :span="12" v-for="item in portfolioCards" :key="item.label">
              <el-card shadow="hover" :class="['portfolio-card', item.color]">
                <div class="portfolio-value">{{ item.value }}</div>
                <div class="portfolio-label">{{ item.label }}</div>
              </el-card>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>交易策略建议</span></template>
          <el-table v-if="tradingStrategies.length" :data="tradingStrategies" border stripe size="small">
            <el-table-column prop="name" label="策略名称" />
            <el-table-column prop="action" label="操作">
              <template #default="{ row }">
                <el-tag :type="row.action === 'sell' ? 'success' : row.action === 'buy' ? 'danger' : 'warning'">
                  {{ row.action === 'sell' ? '卖出' : row.action === 'buy' ? '买入' : '置换' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="asset_type" label="资产类型" />
            <el-table-column prop="volume_tco2" label="交易量 (tCO₂)" />
            <el-table-column prop="target_price_yuan" label="目标价 (元)" />
            <el-table-column prop="expected_revenue_yuan" label="预期收益 (元)" />
          </el-table>
          <el-empty v-else description="暂无交易策略" />
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
  const d = store.carbonAsset.scopeEmissions
  return [
    { label: '总排放 (tCO₂)', value: d?.total_emission_tco2?.toLocaleString() ?? '--', color: 'red' },
    { label: 'Scope 1 (tCO₂)', value: d?.scope_1?.total_tco2?.toLocaleString() ?? '--', color: 'red' },
    { label: 'Scope 2 (tCO₂)', value: d?.scope_2?.total_tco2?.toLocaleString() ?? '--', color: 'orange' },
    { label: 'Scope 3 (tCO₂)', value: d?.scope_3?.total_tco2?.toLocaleString() ?? '--', color: 'blue' },
  ]
})

const emissionDetail = computed(() => {
  const d = store.carbonAsset.scopeEmissions
  if (!d) return []
  const scope1 = (d.scope_1?.breakdown || []).map(item => ({
    category: item.source,
    scope: 'Scope 1',
    value_tco2: item.emission_tco2,
    ratio: item.ratio != null ? `${(item.ratio * 100).toFixed(1)}%` : '--',
  }))
  const scope2 = (d.scope_2?.breakdown || []).map(item => ({
    category: item.source,
    scope: 'Scope 2',
    value_tco2: item.emission_tco2,
    ratio: d.scope_2?.total_tco2 ? `${((item.emission_tco2 / d.scope_2.total_tco2) * 100).toFixed(1)}%` : '--',
  }))
  const scope3 = (d.scope_3?.breakdown || []).map(item => ({
    category: item.source,
    scope: 'Scope 3',
    value_tco2: item.emission_tco2,
    ratio: item.ratio != null ? `${(item.ratio * 100).toFixed(1)}%` : '--',
  }))
  return [...scope1, ...scope2, ...scope3]
})

const portfolioCards = computed(() => {
  const d = store.carbonAsset.portfolio || {}
  const assets = d.assets || []
  const ceaAsset = assets.find(a => a.type?.includes('碳配额'))
  const ccerAssets = assets.filter(a => a.type === 'CCER')
  const gecAsset = assets.find(a => a.type?.includes('绿证'))
  const ccerTotal = ccerAssets.reduce((sum, a) => sum + (a.amount_tco2 || 0), 0)
  return [
    { label: '碳配额 (tCO₂)', value: ceaAsset?.amount_tco2?.toLocaleString() ?? '--', color: 'green' },
    { label: 'CCER (tCO₂)', value: ccerTotal.toLocaleString() ?? '--', color: 'blue' },
    { label: '绿证 (MWh)', value: gecAsset?.amount_mwh?.toLocaleString() ?? '--', color: 'orange' },
    { label: '总价值 (万元)', value: d.total_asset_value_yuan ? (d.total_asset_value_yuan / 10000).toLocaleString() : '--', color: 'purple' },
  ]
})

const tradingStrategies = computed(() => {
  return store.carbonAsset.tradingStrategy?.strategies || []
})

const emissionChartRef = ref(null)
let emissionChart

function initEmissionChart() {
  if (!emissionChartRef.value) return
  emissionChart = echarts.init(emissionChartRef.value)
  const d = store.carbonAsset.scopeEmissions
  emissionChart.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie',
      radius: ['45%', '70%'],
      label: { show: true, formatter: '{b}\n{d}%' },
      data: [
        { value: d?.scope_1?.total_tco2 ?? 0, name: 'Scope 1', itemStyle: { color: '#F56C6C' } },
        { value: d?.scope_2?.total_tco2 ?? 0, name: 'Scope 2', itemStyle: { color: '#E6A23C' } },
        { value: d?.scope_3?.total_tco2 ?? 0, name: 'Scope 3', itemStyle: { color: '#409EFF' } },
      ],
    }],
  })
}

function resizeAll() {
  emissionChart?.resize()
}

onMounted(async () => {
  await nextTick()
  initEmissionChart()
  window.addEventListener('resize', resizeAll)
  await store.fetchScopeEmissions()
  await store.fetchCarbonPortfolio()
  await store.fetchTradingStrategy()
  initEmissionChart()
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeAll)
  emissionChart?.dispose()
})
</script>

<style scoped>
.carbon-asset-page { padding: 4px; }
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
.portfolio-card { text-align: center; }
.portfolio-value { font-size: 22px; font-weight: bold; }
.portfolio-label { font-size: 13px; color: #909399; margin-top: 6px; }
</style>