<template>
  <div class="vpp-page" v-loading="store.vpp.loading">
    <div class="page-header">
      <h3>虚拟电厂 VPP</h3>
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

    <!-- 中层：聚合资源表 -->
    <el-row style="margin-top:20px">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header><span>聚合资源列表</span></template>
          <el-table :data="resourcesTable" border stripe>
            <el-table-column prop="name" label="资源名称" />
            <el-table-column prop="type" label="类型">
              <template #default="{ row }">
                <el-tag :type="typeTagType(row.type)">
                  {{ typeLabel(row.type) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="capacity_kw" label="可调容量 (kW)" />
            <el-table-column prop="response_time_ms" label="响应时间 (ms)" />
            <el-table-column prop="status" label="状态">
              <template #default="{ row }">
                <el-tag :type="row.status === 'online' ? 'success' : 'danger'">
                  {{ row.status === 'online' ? '在线' : '离线' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!resourcesTable.length" description="暂无聚合资源" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 下层：报价表单 + 报价结果 -->
    <el-row :gutter="20" style="margin-top:20px">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>电力市场报价</span></template>
          <el-form :model="bidForm" label-width="110px">
            <el-form-item label="市场类型">
              <el-select v-model="bidForm.marketType" style="width:100%">
                <el-option label="spot 市场" value="spot" />
                <el-option label="辅助服务市场" value="ancillary" />
                <el-option label="容量市场" value="capacity" />
              </el-select>
            </el-form-item>
            <el-form-item label="报价容量 (MWh)">
              <el-input-number v-model="bidForm.volume" :min="0" :max="100" :step="1" style="width:100%" />
            </el-form-item>
            <el-form-item label="报价策略">
              <el-select v-model="bidForm.priceStrategy" style="width:100%">
                <el-option label="竞争性" value="competitive" />
                <el-option label="激进型" value="aggressive" />
                <el-option label="保守型" value="conservative" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleBid" :loading="store.vpp.loading">
                提交报价
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>报价结果</span></template>
          <el-descriptions v-if="bidResult" :column="1" border>
            <el-descriptions-item label="报价编号">{{ bidResult.bid_id }}</el-descriptions-item>
            <el-descriptions-item label="市场类型">{{ bidResult.market_type }}</el-descriptions-item>
            <el-descriptions-item label="中标容量 (kW)">{{ bidResultDisplay.acceptedKw }}</el-descriptions-item>
            <el-descriptions-item label="出清价格 (元/kWh)">{{ bidResultDisplay.clearPrice }}</el-descriptions-item>
            <el-descriptions-item label="预期收益 (元)">{{ bidResult.expected_revenue_yuan?.toLocaleString() }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="bidResult.status === 'submitted' ? 'success' : 'warning'">{{ bidResult.status }}</el-tag>
            </el-descriptions-item>
          </el-descriptions>
          <el-empty v-else description="提交报价后查看结果" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive } from 'vue'
import { useApiStore } from '../stores/api'

const store = useApiStore()

const statCards = computed(() => {
  const status = store.vpp.status
  const aggCap = status?.aggregated_capacity
  return [
    {
      label: '聚合容量 (kW)',
      value: aggCap?.total_capacity_mw != null
        ? (aggCap.total_capacity_mw * 1000).toLocaleString()
        : '--',
      color: 'green',
    },
    {
      label: '上调能力 (kW)',
      value: '0',
      color: 'blue',
    },
    {
      label: '下调能力 (kW)',
      value: '0',
      color: 'orange',
    },
    {
      label: '响应时间 (ms)',
      value: aggCap?.response_time_ms ?? '0',
      color: 'purple',
    },
  ]
})

const resourcesTable = computed(() => {
  const data = store.vpp.resources
  const raw = Array.isArray(data) ? data : (data?.resources || [])
  return raw.map(r => ({
    ...r,
    capacity_kw: (r.capacity_mw != null ? r.capacity_mw * 1000 : 0).toLocaleString(),
    response_time_ms: r.response_time_ms ?? 0,
  }))
})

function typeLabel(type) {
  const map = {
    renewable_generation: '可再生能源',
    energy_storage: '储能',
    grid_connection: '电网',
    flexible_load: '柔性负荷',
  }
  return map[type] || type
}

function typeTagType(type) {
  const map = {
    renewable_generation: 'success',
    energy_storage: 'warning',
    grid_connection: 'info',
    flexible_load: 'primary',
  }
  return map[type] || 'info'
}

const bidForm = reactive({
  marketType: 'spot',
  volume: 10,
  priceStrategy: 'competitive',
})

const bidResult = computed(() => store.vpp.bidResult)

const bidResultDisplay = computed(() => {
  const r = bidResult.value
  if (!r) return { acceptedKw: '--', clearPrice: '--' }
  const acceptedKw = r.cleared_volume_mwh != null
    ? (r.cleared_volume_mwh * 1000).toLocaleString()
    : '0'
  const clearPrice = r.clearing_price_yuan_per_mwh != null
    ? (r.clearing_price_yuan_per_mwh / 1000).toFixed(4)
    : (r.bid_price_yuan_per_kwh != null ? r.bid_price_yuan_per_kwh.toFixed(4) : '0')
  return { acceptedKw, clearPrice }
})

async function handleBid() {
  await store.submitVPPBid({
    market_type: bidForm.marketType,
    volume_mwh: bidForm.volume,
    price_strategy: bidForm.priceStrategy,
  })
}

onMounted(async () => {
  await store.fetchVPPStatus()
  await store.fetchVPPResources()
})
</script>

<style scoped>
.vpp-page { padding: 4px; }
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