<template>
  <div class="storage-page" v-loading="store.storage.loading">
    <div class="page-header">
      <h3>储能优化调度</h3>
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

    <!-- 中层：充放电调度图 -->
    <el-row style="margin-top:20px">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header><span>24h 充放电调度计划</span></template>
          <div ref="scheduleChartRef" style="height: 360px;"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 下层：共享储能商业模式分析 -->
    <el-row :gutter="20" style="margin-top:20px">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header><span>共享储能商业模式分析</span></template>
          <el-row :gutter="20">
            <el-col :span="4" v-for="item in sharedCards" :key="item.label">
              <el-card shadow="hover" :class="['shared-card', item.color]">
                <div class="shared-value">{{ item.value }}</div>
                <div class="shared-label">{{ item.label }}</div>
              </el-card>
            </el-col>
            <el-col :span="4">
              <el-card shadow="hover" class="shared-card purple">
                <div class="shared-value">{{ irrValue }}</div>
                <div class="shared-label">IRR</div>
              </el-card>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import { useApiStore } from '../stores/api'

const store = useApiStore()

const statCards = computed(() => {
  const status = store.storage.status
  return [
    {
      label: '当前 SOC',
      value: status?.battery?.current_soc != null ? `${status.battery.current_soc}%` : '--',
      color: 'green',
    },
    {
      label: '充放电功率 (kW)',
      value: status?.operation?.current_power_kw != null
        ? `${status.operation.current_power_kw > 0 ? '+' : ''}${status.operation.current_power_kw}`
        : '--',
      color: 'blue',
    },
    {
      label: '日峰谷套利收益 (元)',
      value: store.storage.optimizeResult?.summary?.arbitrage_revenue_yuan?.toLocaleString() ?? '--',
      color: 'orange',
    },
    {
      label: '月需量节省 (元)',
      value: '0',
      color: 'purple',
    },
  ]
})

const sharedCards = computed(() => {
  const d = store.storage.sharedStorage || {}
  const models = d.business_models || []
  const leaseModel = models.find(m => m.model === '容量租赁')
  const auxiliaryModel = models.find(m => m.model === '辅助服务')
  const arbitrageModel = models.find(m => m.model === '峰谷套利')
  return [
    {
      label: '容量租赁收入 (万元/年)',
      value: leaseModel?.estimated_annual_revenue_yuan != null
        ? (leaseModel.estimated_annual_revenue_yuan / 10000).toLocaleString()
        : '0',
      color: 'green',
    },
    {
      label: '套利收入 (万元/年)',
      value: arbitrageModel?.estimated_annual_revenue_yuan != null
        ? (arbitrageModel.estimated_annual_revenue_yuan / 10000).toLocaleString()
        : '0',
      color: 'blue',
    },
    {
      label: '辅助服务收入 (万元/年)',
      value: auxiliaryModel?.estimated_annual_revenue_yuan != null
        ? (auxiliaryModel.estimated_annual_revenue_yuan / 10000).toLocaleString()
        : '0',
      color: 'orange',
    },
    {
      label: '回收期 (年)',
      value: d.recommendation?.payback_period_years?.toFixed(1) ?? '--',
      color: 'purple',
    },
  ]
})
const irrValue = computed(() => {
  const irr = store.storage.sharedStorage?.recommendation?.irr_percent
  return irr != null ? `${irr}%` : '--'
})

// 图表
const scheduleChartRef = ref(null)
let scheduleChart

function buildScheduleOption() {
  const schedule = store.storage.optimizeResult?.schedule
  if (!schedule || !schedule.length) {
    const hours = Array.from({ length: 24 }, (_, i) => `${i}:00`)
    return {
      tooltip: { trigger: 'axis' },
      legend: { data: ['充电', '放电'] },
      grid: { left: 50, right: 20, top: 30, bottom: 30 },
      xAxis: { type: 'category', data: hours },
      yAxis: { type: 'value', name: 'kW' },
      series: [
        { name: '充电', type: 'bar', data: new Array(24).fill(0), color: '#67C23A', barWidth: 16 },
        { name: '放电', type: 'bar', data: new Array(24).fill(0), color: '#F56C6C', barWidth: 16 },
      ],
    }
  }

  const hours = schedule.map(s => s.time)
  const charge = schedule.map(s => s.action === 'charge' ? s.power_kw : 0)
  const discharge = schedule.map(s => s.action === 'discharge' ? -s.power_kw : 0)

  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['充电', '放电'] },
    grid: { left: 50, right: 20, top: 30, bottom: 30 },
    xAxis: { type: 'category', data: hours },
    yAxis: { type: 'value', name: 'kW' },
    series: [
      { name: '充电', type: 'bar', data: charge, color: '#67C23A', barWidth: 16 },
      { name: '放电', type: 'bar', data: discharge, color: '#F56C6C', barWidth: 16 },
    ],
  }
}

function initScheduleChart() {
  if (!scheduleChartRef.value) return
  scheduleChart = echarts.init(scheduleChartRef.value)
  scheduleChart.setOption(buildScheduleOption())
}

function resizeAll() {
  scheduleChart?.resize()
}

onMounted(async () => {
  await nextTick()
  initScheduleChart()
  window.addEventListener('resize', resizeAll)
  await store.fetchStorageStatus()
  await store.optimizeStorage()
  await store.fetchSharedStorage()
  if (scheduleChart) {
    scheduleChart.setOption(buildScheduleOption())
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeAll)
  scheduleChart?.dispose()
})
</script>

<style scoped>
.storage-page { padding: 4px; }
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
.shared-card { text-align: center; }
.shared-value { font-size: 24px; font-weight: bold; }
.shared-label { font-size: 13px; color: #909399; margin-top: 6px; }
</style>