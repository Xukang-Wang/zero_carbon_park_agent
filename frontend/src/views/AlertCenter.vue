<template>
  <div class="alert-center">
    <el-card shadow="hover">
      <template #header>
        <span>告警中心</span>
        <el-button type="primary" size="small" @click="loadEvents" :loading="store.alerts.loading" style="margin-left:16px">刷新</el-button>
      </template>
      <el-table v-if="store.alerts.events.length" :data="store.alerts.events" stripe max-height="500" v-loading="store.alerts.loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="severity" label="严重程度" width="100">
          <template #default="{ row }">
            <el-tag :type="row.severity === 'critical' ? 'danger' : 'warning'" size="small">{{ row.severity }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="event_type" label="类型" width="120" />
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="predicted_value" label="预测值" width="100" />
        <el-table-column prop="threshold_value" label="阈值" width="100" />
        <el-table-column prop="detected_at" label="检测时间" width="170">
          <template #default="{ row }">{{ row.detected_at?.slice(0, 16) || '--' }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'open' ? 'danger' : row.status === 'in_progress' ? 'warning' : 'success'" size="small">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="triggerWorkflow(row)">触发处置</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-skeleton v-if="store.alerts.loading" :rows="6" animated />
      <el-empty v-if="!store.alerts.events.length && !store.alerts.loading" description="暂无告警事件" />
      <el-alert v-if="loadError" :title="loadError" type="error" show-icon closable @close="loadError = ''" style="margin-top:12px" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useApiStore } from '../stores/api'
import { ElMessage } from 'element-plus'

const store = useApiStore()
const loadError = ref('')

onMounted(() => loadEvents())

async function loadEvents() {
  try {
    loadError.value = ''
    await store.fetchAlerts()
  } catch (e) {
    loadError.value = '加载告警数据失败: ' + (e.message || '未知错误')
  }
}

async function triggerWorkflow(row) {
  try {
    await store.triggerWorkflow('water_anomaly', {
      device_id: row.source || 'WQ-001',
      anomaly_type: row.event_type || 'cod_exceeded',
      predicted_value: row.predicted_value || 320,
      threshold: row.threshold_value || 300,
    })
    ElMessage.success('工作流已触发，正在执行...')
    loadEvents()
  } catch {
    ElMessage.error('工作流触发失败')
  }
}
</script>