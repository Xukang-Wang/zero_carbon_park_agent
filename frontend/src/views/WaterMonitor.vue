<template>
  <div class="water-monitor">
    <el-card shadow="hover">
      <template #header>
        <span>水质监测数据</span>
        <el-select v-model="deviceId" style="width:150px;margin-left:16px">
          <el-option label="WQ-001" value="WQ-001" />
          <el-option label="WQ-002" value="WQ-002" />
        </el-select>
        <el-button type="primary" @click="loadData" :loading="store.water.loading" style="margin-left:12px">刷新</el-button>
        <el-button type="success" @click="predict" :loading="store.water.predicting">24h预测</el-button>
      </template>
      <el-alert v-if="chartError" title="加载失败" :description="chartError" type="error" show-icon closable @close="chartError = ''" style="margin-bottom:12px" />
      <div v-if="!store.water.loading && !chartError" ref="chartRef" style="height: 380px;"></div>
      <el-skeleton v-if="store.water.loading" :rows="8" animated style="padding:20px" />
      <el-empty v-if="!store.water.loading && !chartError && !store.water.history?.length" description="暂无水质监测数据" />
    </el-card>

    <!-- 第二行：辅助指标图表 -->
    <el-row :gutter="20" style="margin-top:20px">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>pH · 温度 · 溶解氧</span></template>
          <div v-if="!store.water.loading" ref="chart2Ref" style="height: 320px;"></div>
          <el-skeleton v-else :rows="6" animated style="padding:20px" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>进水流量 · 污泥浓度</span></template>
          <div v-if="!store.water.loading" ref="chart3Ref" style="height: 320px;"></div>
          <el-skeleton v-else :rows="6" animated style="padding:20px" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top:20px">
      <el-col :span="12">
        <el-card shadow="hover" v-loading="store.water.predicting">
          <template #header><span>预测结果（未来24h）</span></template>
          <el-table v-if="store.water.predictions?.length" :data="paginatedPredictions" size="small" max-height="420">
            <el-table-column prop="target_timestamp" label="时间" width="180" />
            <el-table-column prop="cod" label="COD (mg/L)">
              <template #default="{ row }">
                <span :style="{ color: row.cod > 300 ? '#F56C6C' : row.cod > 250 ? '#E6A23C' : '#303133' }">{{ row.cod }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="ammonia_nitrogen" label="氨氮 (mg/L)">
              <template #default="{ row }">
                <span :style="{ color: row.ammonia_nitrogen > 35 ? '#F56C6C' : row.ammonia_nitrogen > 25 ? '#E6A23C' : '#303133' }">{{ row.ammonia_nitrogen }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="nitrate_nitrogen" label="硝氮 (mg/L)">
              <template #default="{ row }">
                <span :style="{ color: row.nitrate_nitrogen > 5 ? '#F56C6C' : row.nitrate_nitrogen > 3 ? '#E6A23C' : '#303133' }">{{ row.nitrate_nitrogen }}</span>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination
            v-if="store.water.predictions?.length > pageSize"
            v-model:current-page="currentPage"
            :page-size="pageSize"
            :total="store.water.predictions?.length || 0"
            layout="total, prev, pager, next"
            size="small"
            style="margin-top:12px;justify-content:flex-end"
          />
          <el-empty v-else-if="!store.water.predicting" description="暂无预测数据，请点击24h预测" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>异常告警</span></template>
          <template v-if="store.water.anomalyFlags?.length">
            <el-alert
              v-for="(a, i) in store.water.anomalyFlags" :key="i"
              :title="`[${a.severity}] ${a.metric}: ${a.predicted_value} > ${a.threshold}`"
              :type="a.severity === 'critical' ? 'error' : 'warning'"
              :description="`预测时间: ${a.target_timestamp}`"
              show-icon style="margin-bottom: 10px"
            />
          </template>
          <el-empty v-else description="暂无异常告警" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import { useApiStore } from '../stores/api'

const store = useApiStore()
const deviceId = ref('WQ-001')
const chartRef = ref(null)
const chart2Ref = ref(null)
const chart3Ref = ref(null)
let chartInstance = null
let chart2Instance = null
let chart3Instance = null
const chartError = ref('')

const currentPage = ref(1)
const pageSize = ref(10)

const paginatedPredictions = computed(() => {
  const data = store.water.predictions || []
  const start = (currentPage.value - 1) * pageSize.value
  return data.slice(start, start + pageSize.value)
})

async function loadData() {
  chartError.value = ''
  try {
    await store.fetchWaterHistory(deviceId.value)
    if (store.water.error) {
      chartError.value = store.water.error
      return
    }
  } catch (e) {
    chartError.value = e.message || '数据加载失败'
    return
  }
  await nextTick()
  renderMainChart()
  renderAuxCharts()
}

async function predict() {
  await store.predictWater(deviceId.value)
}

function getTimeLabels(records) {
  return records.length
    ? records.map(r => r.timestamp?.slice(11, 16) || '--')
    : Array.from({ length: 24 }, (_, i) => `${i}:00`)
}

function renderMainChart() {
  if (!chartRef.value) return
  if (!chartInstance) chartInstance = echarts.init(chartRef.value)

  const records = store.water.history
  const times = getTimeLabels(records)
  const cod = records.length ? records.map(r => r.cod ?? 0) : []
  const nh3 = records.length ? records.map(r => r.ammonia_nitrogen ?? 0) : []
  const no3 = records.length ? records.map(r => r.nitrate_nitrogen ?? 0) : []

  chartInstance.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['COD', '氨氮', '硝氮'] },
    xAxis: { type: 'category', data: times },
    yAxis: [
      { type: 'value', name: 'COD (mg/L)' },
      { type: 'value', name: '氨氮/硝氮 (mg/L)' },
    ],
    series: [
      { name: 'COD', type: 'line', data: cod, smooth: true,
        markLine: { silent: true, data: [{ yAxis: 300, name: '严重阈值', lineStyle: { color: '#F56C6C' } }, { yAxis: 250, name: '告警阈值', lineStyle: { color: '#E6A23C' } }] },
      },
      { name: '氨氮', type: 'line', yAxisIndex: 1, data: nh3, smooth: true },
      { name: '硝氮', type: 'line', yAxisIndex: 1, data: no3, smooth: true },
    ],
  })
}

function renderAuxCharts() {
  const records = store.water.history
  const times = getTimeLabels(records)

  // pH · 温度 · 溶解氧
  if (chart2Ref.value) {
    if (!chart2Instance) chart2Instance = echarts.init(chart2Ref.value)
    chart2Instance.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['pH', '温度(℃)', '溶解氧(mg/L)'] },
      xAxis: { type: 'category', data: times },
      yAxis: [
        { type: 'value', name: 'pH', min: 5, max: 10 },
        { type: 'value', name: '温度/DO' },
      ],
      series: [
        { name: 'pH', type: 'line', data: records.map(r => r.ph ?? 0), smooth: true, color: '#9C27B0' },
        { name: '温度(℃)', type: 'line', yAxisIndex: 1, data: records.map(r => r.temperature ?? 0), smooth: true, color: '#E6A23C' },
        { name: '溶解氧(mg/L)', type: 'line', yAxisIndex: 1, data: records.map(r => r.dissolved_oxygen ?? 0), smooth: true, color: '#409EFF' },
      ],
    })
  }

  // 进水流量 · 污泥浓度
  if (chart3Ref.value) {
    if (!chart3Instance) chart3Instance = echarts.init(chart3Ref.value)
    chart3Instance.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['进水流量(m³/h)', '污泥浓度(mg/L)'] },
      xAxis: { type: 'category', data: times },
      yAxis: [
        { type: 'value', name: '进水流量(m³/h)' },
        { type: 'value', name: '污泥浓度(mg/L)' },
      ],
      series: [
        { name: '进水流量(m³/h)', type: 'bar', data: records.map(r => r.inflow_rate ?? 0), color: '#67C23A', barWidth: '60%' },
        { name: '污泥浓度(mg/L)', type: 'line', yAxisIndex: 1, data: records.map(r => r.sludge_conc ?? 0), smooth: true, color: '#909399' },
      ],
    })
  }
}

watch(deviceId, () => loadData())

onMounted(async () => {
  await nextTick()
  loadData()
  window.addEventListener('resize', () => {
    chartInstance?.resize()
    chart2Instance?.resize()
    chart3Instance?.resize()
  })
})

onUnmounted(() => {
  chartInstance?.dispose()
  chart2Instance?.dispose()
  chart3Instance?.dispose()
})
</script>