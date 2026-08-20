<template>
  <div class="park-monitor">
    <el-page-header @back="$router.push('/')" title="返回驾驶舱">
      <template #content>
        <span class="page-title">园区节点智能监测</span>
        <el-tag :type="systemStatusType" size="small" style="margin-left:12px">{{ systemStatus }}</el-tag>
      </template>
    </el-page-header>

    <!-- 源侧：发电节点 -->
    <el-card shadow="hover" style="margin-top:16px">
      <template #header><span style="font-weight:bold">源侧 - 发电节点</span></template>
      <el-row :gutter="16">
        <el-col :span="8" v-for="gen in genNodes" :key="gen.id">
          <el-card :class="['node-card', gen.status === 'online' ? 'online' : 'offline']">
            <template #header>
              <span>{{ gen.name }}</span>
              <el-tag :type="gen.status === 'online' ? 'success' : 'danger'" size="small" style="float:right">{{ gen.status === 'online' ? '在线' : '离线' }}</el-tag>
            </template>
            <div class="node-body">
              <div class="node-power">{{ gen.power }} <span class="unit">kW</span></div>
              <el-progress :percentage="gen.loadFactor" :color="gen.loadFactor > 80 ? '#F56C6C' : '#67C23A'" />
              <div class="node-info">{{ gen.info }}</div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </el-card>

    <!-- 网侧 -->
    <el-card shadow="hover" style="margin-top:16px">
      <template #header><span style="font-weight:bold">网侧 - 微电网与电网交互</span></template>
      <el-row :gutter="16">
        <el-col :span="8">
          <div class="grid-status">
            <div class="big-number">{{ gridData.voltage }} <span class="unit">kV</span></div>
            <div class="label">电压等级</div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="grid-status" :style="{color: gridData.isImporting ? '#E6A23C' : '#67C23A'}">
            <div class="big-number">{{ gridData.power }} <span class="unit">kW</span></div>
            <div class="label">{{ gridData.isImporting ? '购电中' : '售电中' }}</div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="grid-status">
            <div class="big-number">{{ gridData.selfSufficiency }} <span class="unit">%</span></div>
            <div class="label">自给自足率</div>
          </div>
        </el-col>
      </el-row>
      <el-row :gutter="16" style="margin-top:12px">
        <el-col :span="12">
          <el-descriptions :column="1" size="small" border>
            <el-descriptions-item label="频率">{{ gridData.frequency }} Hz</el-descriptions-item>
            <el-descriptions-item label="功率平衡">{{ gridData.powerBalance }} kW</el-descriptions-item>
            <el-descriptions-item label="可再生占比">{{ gridData.renewableRatio }}%</el-descriptions-item>
          </el-descriptions>
        </el-col>
        <el-col :span="12">
          <el-descriptions :column="1" size="small" border>
            <el-descriptions-item label="碳排放强度">{{ gridData.carbonIntensity }} tCO₂/MWh</el-descriptions-item>
            <el-descriptions-item label="总发电">{{ gridData.totalGen }} kW</el-descriptions-item>
            <el-descriptions-item label="总负荷">{{ gridData.totalLoad }} kW</el-descriptions-item>
          </el-descriptions>
        </el-col>
      </el-row>
    </el-card>

    <!-- 荷侧 -->
    <el-card shadow="hover" style="margin-top:16px">
      <template #header>
        <span style="font-weight:bold">荷侧 - 负荷节点</span>
        <el-tag size="small" style="margin-left:8px">总需求响应容量: {{ drCapacity }} kW</el-tag>
      </template>
      <el-table :data="loadNodes" size="small" stripe>
        <el-table-column prop="name" label="名称" width="160" />
        <el-table-column prop="type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ row.type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="power_kw" label="功率 (kW)" width="100" />
        <el-table-column prop="flexibility" label="柔性等级" width="100">
          <template #default="{ row }">
            <el-tag :type="flexTagType(row.flexibility)" size="small">{{ row.flexibility }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="dr_capacity_kw" label="DR容量 (kW)" width="120" />
        <el-table-column label="功率占比" min-width="150">
          <template #default="{ row }">
            <el-progress :percentage="row.powerRatio" :color="row.flexibility === 'fixed' ? '#909399' : '#67C23A'" />
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'online' ? 'success' : 'danger'" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 储侧 -->
    <el-card shadow="hover" style="margin-top:16px">
      <template #header><span style="font-weight:bold">储侧 - 储能系统</span></template>
      <el-row :gutter="16">
        <el-col :span="10">
          <div :ref="socDetailChart.container" style="height: 250px;"></div>
        </el-col>
        <el-col :span="14">
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="SOC">{{ storageData.soc }}%</el-descriptions-item>
            <el-descriptions-item label="SOH">{{ storageData.soh }}%</el-descriptions-item>
            <el-descriptions-item label="容量">{{ storageData.capacity }} kWh</el-descriptions-item>
            <el-descriptions-item label="额定功率">{{ storageData.ratedPower }} kW</el-descriptions-item>
            <el-descriptions-item label="当前功率">{{ storageData.currentPower }} kW</el-descriptions-item>
            <el-descriptions-item label="运行模式">{{ storageData.mode }}</el-descriptions-item>
            <el-descriptions-item label="循环次数">{{ storageData.cycles }}</el-descriptions-item>
            <el-descriptions-item label="剩余循环">{{ storageData.remainingCycles }}</el-descriptions-item>
            <el-descriptions-item label="温度">{{ storageData.temp }}°C</el-descriptions-item>
            <el-descriptions-item label="寿命进度">{{ storageData.lifetimeProgress }}%</el-descriptions-item>
            <el-descriptions-item label="可用能量">{{ storageData.availableEnergy }} kWh</el-descriptions-item>
            <el-descriptions-item label="放电能力">{{ storageData.dischargeable }} kWh</el-descriptions-item>
          </el-descriptions>
        </el-col>
      </el-row>
    </el-card>

    <!-- VPP聚合 -->
    <el-card shadow="hover" style="margin-top:16px">
      <template #header><span style="font-weight:bold">虚拟电厂 (VPP) 聚合</span></template>
      <el-row :gutter="16">
        <el-col :span="6" v-for="item in vppItems" :key="item.label">
          <div class="vpp-metric">
            <div class="vpp-value">{{ item.value }}</div>
            <div class="vpp-label">{{ item.label }}</div>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import * as echarts from 'echarts'
import { useApiStore } from '../stores/api'
import { useChart } from '../composables/useChart'

const store = useApiStore()

const snap = computed(() => store.park.snapshot)
const systemStatus = computed(() => {
  const s = snap.value?.alerts?.system_status
  return s === 'normal' ? '正常' : s === 'warning' ? '告警' : '异常'
})
const systemStatusType = computed(() => {
  const s = snap.value?.alerts?.system_status
  return s === 'normal' ? 'success' : s === 'warning' ? 'warning' : 'danger'
})

const genNodes = computed(() => {
  const s = snap.value
  if (!s) return []
  const pv = s.generation?.pv
  const wind = s.generation?.wind
  const bio = s.generation?.biomass_chp
  return [
    {
      id: pv?.id ?? 'PV-001',
      name: pv?.name ?? '1号光伏电站',
      status: pv?.status === 'running' ? 'online' : 'offline',
      power: pv?.current_power_kw?.toFixed(0) ?? '0',
      loadFactor: Number(((pv?.current_power_kw ?? 0) / (pv?.capacity_kw || 5000) * 100).toFixed(0)),
      info: `容量: ${pv?.capacity_kw ?? 5000} kW · 今日发电: ${pv?.generation_today_kwh ?? 0} kWh`,
    },
    {
      id: wind?.id ?? 'WIND-001',
      name: wind?.name ?? '1号风力发电场',
      status: wind?.status === 'running' ? 'online' : 'offline',
      power: wind?.current_power_kw?.toFixed(0) ?? '0',
      loadFactor: Number(((wind?.current_power_kw ?? 0) / (wind?.capacity_kw || 3000) * 100).toFixed(0)),
      info: `容量: ${wind?.capacity_kw ?? 3000} kW · 今日发电: ${wind?.generation_today_kwh ?? 0} kWh`,
    },
    {
      id: bio?.id ?? 'BIO-001',
      name: bio?.name ?? '生物质CHP',
      status: 'online',
      power: bio?.current_electric_kw?.toFixed(0) ?? '0',
      loadFactor: Number(((bio?.current_electric_kw ?? 0) / (bio?.capacity_kw || 3000) * 100).toFixed(0)),
      info: `热电联产 · 总效率: ${bio?.total_efficiency ?? '--'}%`,
    },
  ]
})

const gridData = computed(() => {
  const s = snap.value
  const carbonIntensity = (() => {
    const emission = s?.carbon?.current_emission_tco2_per_h
    const loadKw = s?.loads?.total_power_kw
    if (emission != null && loadKw && loadKw > 0) {
      return (emission / loadKw * 1000).toFixed(4)
    }
    return '0'
  })()
  return {
    voltage: s?.grid?.voltage_kv?.toFixed(1) ?? '10.0',
    power: s?.grid?.current_power_kw?.toFixed(0) ?? '0',
    isImporting: s?.grid?.is_importing ?? true,
    selfSufficiency: s?.micro_grid?.self_sufficiency_rate?.toFixed(1) ?? '0',
    frequency: '50.0',
    powerBalance: s?.micro_grid?.power_balance?.toFixed(0) ?? '0',
    renewableRatio: s?.micro_grid?.renewable_ratio?.toFixed(1) ?? '0',
    carbonIntensity,
    totalGen: s?.micro_grid?.total_generation_kw?.toFixed(0) ?? '0',
    totalLoad: s?.micro_grid?.total_load_kw?.toFixed(0) ?? '0',
  }
})

const loadNodes = computed(() => {
  const items = snap.value?.loads?.breakdown || []
  const total = snap.value?.loads?.total_power_kw || 1
  return items.map(l => ({
    name: l.name,
    type: l.type,
    power_kw: l.current_power_kw ?? 0,
    flexibility: l.flexibility ?? 'fixed',
    dr_capacity_kw: 0,
    powerRatio: Math.round((l.current_power_kw ?? 0) / total * 100),
    status: l.flexibility === 'fixed' ? 'online' : 'online',
  }))
})

const drCapacity = computed(() => snap.value?.loads?.demand_response_capacity_kw?.toFixed(0) ?? '0')

const storageData = computed(() => {
  const s = snap.value?.storage
  const cycles = s?.cycle_count ?? 0
  const maxDesignCycles = 6000
  return {
    soc: s?.current_soc?.toFixed(1) ?? '0',
    soh: s?.state_of_health?.toFixed(1) ?? '0',
    capacity: s?.capacity_kwh ?? '0',
    ratedPower: s?.rated_power_kw ?? '0',
    currentPower: s?.current_power_kw?.toFixed(0) ?? '0',
    mode: s?.mode ?? 'idle',
    cycles,
    remainingCycles: cycles,
    temp: s?.temperature_c?.toFixed(1) ?? '0',
    lifetimeProgress: (cycles / maxDesignCycles * 100).toFixed(1),
    availableEnergy: s?.available_energy_kwh?.toFixed(1) ?? '0',
    dischargeable: s?.remaining_discharge_kwh?.toFixed(1) ?? '0',
  }
})

const vppItems = computed(() => {
  const v = store.park.vppAggregation
  return [
    { label: '聚合容量', value: `${v?.aggregated_capacity_mw ?? '--'} MW` },
    { label: '可再生发电', value: `${v?.breakdown?.renewable_generation_mw ?? '--'} MW` },
    { label: '柔性负荷', value: `${v?.breakdown?.flexible_load_mw ?? '--'} MW` },
    { label: '储能', value: `${v?.breakdown?.energy_storage_mw ?? '--'} MW` },
  ]
})

function flexTagType(flex) {
  const map = { fixed: 'info', shiftable: 'warning', curtailable: 'warning', flexible: 'success' }
  return map[flex] || 'info'
}

// SOC详情图 —— 基于快照中储能实际数据
const socDetailChart = useChart(() => {
  const s = snap.value?.storage
  const currentSoc = s?.current_soc ?? 62.5
  const currentPower = s?.current_power_kw ?? 850
  // 基于当前 SOC 生成 24 小时趋势：当前小时为最新值，向前反推
  const hours = Array.from({ length: 24 }, (_, i) => `${i}:00`)
  const socData = []
  const powerData = []
  let socCursor = currentSoc
  for (let i = 23; i >= 0; i--) {
    socData[i] = Math.round(socCursor * 10) / 10
    // 模拟小幅波动：充电/放电趋势
    const delta = (Math.sin(i / 24 * Math.PI * 2 - Math.PI / 2) * 3 + (Math.random() - 0.5) * 2)
    socCursor = Math.max(0, Math.min(100, socCursor - delta))
    powerData[i] = Math.round(delta * 50)
  }
  return {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: hours },
    yAxis: [
      { type: 'value', name: 'SOC (%)', min: 0, max: 100 },
      { type: 'value', name: '功率 (kW)' },
    ],
    series: [
      {
        name: 'SOC', type: 'line', smooth: true,
        data: socData,
        markLine: { data: [{ yAxis: 20, name: '最低', lineStyle: { color: '#F56C6C' } }, { yAxis: 90, name: '最高', lineStyle: { color: '#67C23A' } }] },
        color: '#9C27B0',
      },
      {
        name: '功率', type: 'bar', yAxisIndex: 1,
        data: powerData,
        color: '#409EFF',
      },
    ],
  }
})

onMounted(async () => {
  await Promise.all([
    store.fetchParkSnapshot(),
    store.fetchVPPAggregation(),
  ])
  socDetailChart.update()
})
</script>

<style scoped>
.park-monitor { padding: 4px; }
.page-title { font-size: 18px; font-weight: bold; }
.node-card { text-align: center; }
.node-card.online { border-left: 3px solid #67C23A; }
.node-card.offline { border-left: 3px solid #F56C6C; }
.node-body { padding: 4px 0; }
.node-power { font-size: 32px; font-weight: bold; color: #303133; }
.node-power .unit { font-size: 14px; color: #909399; }
.node-info { font-size: 12px; color: #909399; margin-top: 8px; }
.grid-status { text-align: center; padding: 16px; }
.big-number { font-size: 36px; font-weight: bold; }
.big-number .unit { font-size: 16px; color: #909399; }
.label { font-size: 13px; color: #909399; margin-top: 4px; }
.vpp-metric { text-align: center; padding: 12px; }
.vpp-value { font-size: 24px; font-weight: bold; color: #303133; }
.vpp-label { font-size: 13px; color: #909399; margin-top: 4px; }
</style>