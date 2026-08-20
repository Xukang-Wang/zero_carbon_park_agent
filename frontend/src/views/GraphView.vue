<template>
  <div class="graph-view">
    <el-card shadow="hover">
      <template #header>
        <span>能源知识图谱</span>
        <el-button type="primary" size="small" @click="loadOverview" :loading="store.graph.loading" style="margin-left:16px">刷新</el-button>
      </template>
      <div v-if="!store.graph.loading" ref="graphChartRef" style="height: 500px;"></div>
      <el-skeleton v-else :rows="12" animated style="padding:20px;height:500px" />
    </el-card>

    <el-row :gutter="20" style="margin-top:20px">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>能源血缘追溯</span></template>
          <el-select v-model="traceEntity" style="width:200px" @change="traceEnergy">
            <el-option label="污水处理厂 (WWTP-001)" value="WWTP-001" />
            <el-option label="1号生产线 (LOAD-001)" value="LOAD-001" />
            <el-option label="2号生产线 (LOAD-002)" value="LOAD-002" />
            <el-option label="光伏电站 (PV-001)" value="PV-001" />
          </el-select>
          <el-button type="primary" @click="traceEnergy" style="margin-left:12px">追溯</el-button>
          <div v-if="store.graph.traceResult?.length" style="margin-top:16px">
            <el-timeline>
              <el-timeline-item
                v-for="(item, i) in store.graph.traceResult" :key="i"
                :timestamp="`深度 ${item.depth}`"
              >
                {{ item.from }} → {{ item.to }} ({{ item.relation }}, {{ item.power_kw }} kW)
              </el-timeline-item>
            </el-timeline>
          </div>
          <el-empty v-else description="选择实体后点击追溯" style="margin-top:20px" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>图谱概览</span></template>
          <el-descriptions :column="1" border v-if="store.graph.overview" v-loading="store.graph.loading">
            <el-descriptions-item label="总节点数">{{ store.graph.overview.total_nodes }}</el-descriptions-item>
            <el-descriptions-item label="总边数">{{ store.graph.overview.total_edges }}</el-descriptions-item>
            <el-descriptions-item label="能源源节点">{{ store.graph.overview.node_counts?.EnergySource || 0 }}</el-descriptions-item>
            <el-descriptions-item label="电网节点">{{ store.graph.overview.node_counts?.GridNode || 0 }}</el-descriptions-item>
            <el-descriptions-item label="负荷节点">{{ store.graph.overview.node_counts?.EnergyLoad || 0 }}</el-descriptions-item>
            <el-descriptions-item label="储能节点">{{ store.graph.overview.node_counts?.EnergyStorage || 0 }}</el-descriptions-item>
            <el-descriptions-item label="可再生能源容量">{{ store.graph.overview.total_renewable_capacity_kw }} kW</el-descriptions-item>
            <el-descriptions-item label="可再生能源占比">{{ store.graph.overview.renewable_ratio ? (store.graph.overview.renewable_ratio * 100).toFixed(1) + '%' : '--' }}</el-descriptions-item>
          </el-descriptions>
          <el-empty v-else description="加载中..." />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { useApiStore } from '../stores/api'

const store = useApiStore()
const graphChartRef = ref(null)
const traceEntity = ref('WWTP-001')
let graphChart = null

async function loadOverview() {
  await store.fetchGraphOverview()
  renderGraph()
}

function renderGraph() {
  if (!graphChartRef.value) return
  if (!graphChart) graphChart = echarts.init(graphChartRef.value)

  // 从 API 构建图谱数据，API 不可用时回退到默认数据
  const overview = store.graph.overview
  graphChart.setOption({
    tooltip: { formatter: '{b}' },
    series: [{
      type: 'graph',
      layout: 'force',
      roam: true,
      label: { show: true, fontSize: 12 },
      force: { repulsion: 300, edgeLength: 150 },
      data: [
        { name: '光伏电站', category: 0, symbolSize: 40, value: overview?.total_renewable_capacity_kw },
        { name: '市电', category: 0, symbolSize: 35 },
        { name: '变压器', category: 1, symbolSize: 30 },
        { name: '污水处理厂', category: 2, symbolSize: 35 },
        { name: '1号生产线', category: 2, symbolSize: 30 },
        { name: '2号生产线', category: 2, symbolSize: 30 },
        { name: '空调系统', category: 2, symbolSize: 25 },
        { name: '充电桩', category: 2, symbolSize: 25 },
        { name: '储能系统', category: 3, symbolSize: 30 },
        { name: '碳排放', category: 4, symbolSize: 28 },
      ],
      categories: [
        { name: '能源源', itemStyle: { color: '#67C23A' } },
        { name: '电网', itemStyle: { color: '#409EFF' } },
        { name: '负荷', itemStyle: { color: '#E6A23C' } },
        { name: '储能', itemStyle: { color: '#9C27B0' } },
        { name: '碳排放', itemStyle: { color: '#F56C6C' } },
      ],
      links: [
        { source: '光伏电站', target: '变压器', label: { show: true, formatter: '发电' } },
        { source: '市电', target: '变压器', label: { show: true, formatter: '供电' } },
        { source: '变压器', target: '污水处理厂', label: { show: true, formatter: '输电' } },
        { source: '变压器', target: '1号生产线', label: { show: true, formatter: '输电' } },
        { source: '变压器', target: '2号生产线', label: { show: true, formatter: '输电' } },
        { source: '变压器', target: '空调系统', label: { show: true, formatter: '输电' } },
        { source: '变压器', target: '充电桩', label: { show: true, formatter: '输电' } },
        { source: '变压器', target: '储能系统', label: { show: true, formatter: '充电' } },
        { source: '储能系统', target: '变压器', label: { show: true, formatter: '放电' } },
        { source: '1号生产线', target: '碳排放', label: { show: true, formatter: '排放' } },
        { source: '污水处理厂', target: '碳排放', label: { show: true, formatter: '排放' } },
      ],
    }],
  })
}

async function traceEnergy() {
  await store.traceEnergy(traceEntity.value)
}

onMounted(async () => {
  await nextTick()
  await loadOverview()
  window.addEventListener('resize', () => graphChart?.resize())
})

onUnmounted(() => {
  graphChart?.dispose()
})
</script>