<template>
  <div class="evaluation-page" v-loading="store.evaluation.loading">
    <div class="page-header">
      <h3>零碳园区评价</h3>
      <el-divider />
    </div>

    <!-- 总分 + 等级 -->
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card shadow="hover" style="text-align:center;padding:30px">
          <div ref="scoreChartRef" style="height: 220px;width:220px;margin:0 auto"></div>
          <div style="font-size:14px;color:#909399;margin-top:4px">综合评价得分</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" style="text-align:center;padding:30px">
          <div class="grade-badge" :style="{ color: gradeColor }">{{ gradeLabel }}</div>
          <div style="font-size:14px;color:#909399;margin-top:8px">评价等级</div>
          <div style="font-size:12px;color:#c0c4cc;margin-top:4px">{{ standardName }}</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" style="text-align:center;padding:30px">
          <el-progress type="dashboard" :percentage="certProgressPct" :color="certProgressColor" :stroke-width="12" style="margin:0 auto" />
          <div style="font-size:14px;color:#909399;margin-top:8px">认证整体进度</div>
          <div style="font-size:12px;color:#c0c4cc;margin-top:4px">预计 {{ estimatedCompletion }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 分类指标详情 -->
    <el-row style="margin-top:20px">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header><span>评价指标明细</span></template>
          <el-collapse v-model="activeCategories">
            <el-collapse-item v-for="cat in allCategories" :key="cat.name" :name="cat.name">
              <template #title>
                <div style="display:flex;align-items:center;justify-content:space-between;width:100%">
                  <span><b>{{ cat.name }}</b>（权重 {{ (cat.weight * 100).toFixed(0) }}%）</span>
                  <el-tag size="small" effect="plain">{{ cat.avgScore.toFixed(0) }}分</el-tag>
                </div>
              </template>
              <el-table :data="cat.indicators" size="small" stripe>
                <el-table-column prop="name" label="指标名称" min-width="160" />
                <el-table-column prop="current_value" label="当前值" width="120" align="center">
                  <template #default="{ row }">{{ row.current_value }} {{ row.unit }}</template>
                </el-table-column>
                <el-table-column prop="target" label="目标值" width="120" align="center" />
                <el-table-column label="得分" width="90" align="center">
                  <template #default="{ row }">
                    <el-tag :type="statusTagType(row.status)" size="small">{{ row.score }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="状态" width="80" align="center">
                  <template #default="{ row }">
                    <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
                  </template>
                </el-table-column>
              </el-table>
            </el-collapse-item>
          </el-collapse>
        </el-card>
      </el-col>
    </el-row>

    <!-- 认证里程碑 -->
    <el-row style="margin-top:20px">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header><span>认证进度 · 里程碑</span></template>
          <el-steps :active="certActiveStep" finish-status="success" align-center v-if="certStepsDisplay.length">
            <el-step
              v-for="step in certStepsDisplay"
              :key="step.name"
              :title="step.name"
              :description="step.description"
              :status="step._status"
            />
          </el-steps>
          <el-empty v-else description="暂无认证进度数据" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 关键差距 -->
    <el-row style="margin-top:20px">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header><span>关键差距与行动建议</span></template>
          <el-table :data="keyGaps" size="small" stripe>
            <el-table-column prop="area" label="领域" width="160" />
            <el-table-column prop="current" label="当前值" width="140" align="center" />
            <el-table-column prop="target" label="目标值" width="140" align="center" />
            <el-table-column prop="gap" label="差距" width="100" align="center">
              <template #default="{ row }"><el-tag type="danger" size="small">{{ row.gap }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="action" label="行动建议" min-width="260" />
          </el-table>
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
const activeCategories = ref(['能源结构'])

// ── 总分等级 ──
const scoreStatus = computed(() => {
  const score = store.evaluation.indicators?.total_score ?? 0
  if (score >= 80) return { type: 'success', label: '优秀' }
  if (score >= 60) return { type: 'warning', label: '合格' }
  return { type: 'danger', label: '未达标' }
})

const gradeLabel = computed(() => store.evaluation.indicators?.grade ?? '--')
const gradeColor = computed(() => {
  const g = gradeLabel.value
  if (g.includes('三星') || g.includes('四星') || g.includes('五星')) return '#67C23A'
  if (g.includes('二星')) return '#409EFF'
  return '#E6A23C'
})
const standardName = computed(() => store.evaluation.indicators?.standard ?? '')

// ── 认证进度 ──
const certProgressPct = computed(() => store.evaluation.certProgress?.overall_progress ?? 0)
const certProgressColor = computed(() => {
  const p = certProgressPct.value
  if (p >= 80) return '#67C23A'
  if (p >= 50) return '#409EFF'
  return '#E6A23C'
})
const estimatedCompletion = computed(() => store.evaluation.certProgress?.estimated_completion ?? '--')

// ── 分类指标 ──
const allCategories = computed(() => {
  const cats = store.evaluation.indicators?.categories || []
  return cats.map(c => ({
    ...c,
    avgScore: c.indicators.length ? c.indicators.reduce((s, i) => s + i.score, 0) / c.indicators.length : 0,
  }))
})

function statusTagType(status) {
  return { pass: 'success', warning: 'warning', critical: 'danger' }[status] || 'info'
}
function statusLabel(status) {
  return { pass: '达标', warning: '预警', critical: '未达标' }[status] || status
}

// ── 认证里程碑 ──
const certStepsDisplay = computed(() => {
  const milestones = store.evaluation.certProgress?.milestones || []
  return milestones.map(m => ({
    ...m,
    _status: m.status === 'completed' ? 'success' : m.status === 'in_progress' ? 'process' : 'wait',
  }))
})

const certActiveStep = computed(() => {
  const steps = certStepsDisplay.value
  const activeIdx = steps.findIndex(s => s.status === 'in_progress')
  return activeIdx >= 0 ? activeIdx : steps.length
})

// ── 关键差距 ──
const keyGaps = computed(() => store.evaluation.certProgress?.key_gaps || [])

// ── 总分仪表盘 ──
const scoreChartRef = ref(null)
let scoreChart

function initScoreChart() {
  if (!scoreChartRef.value) return
  if (scoreChart) scoreChart.dispose()
  scoreChart = echarts.init(scoreChartRef.value)
  const score = store.evaluation.indicators?.total_score ?? 0
  scoreChart.setOption({
    series: [{
      type: 'gauge',
      startAngle: 210, endAngle: -30,
      center: ['50%', '60%'], radius: '90%',
      min: 0, max: 100,
      splitNumber: 5,
      axisLine: { lineStyle: { width: 16, color: [[0.3, '#F56C6C'], [0.6, '#E6A23C'], [0.8, '#409EFF'], [1, '#67C23A']] } },
      axisTick: { show: false },
      axisLabel: { distance: 18, fontSize: 10 },
      pointer: { length: '60%', width: 6 },
      detail: { valueAnimation: true, formatter: '{value}', fontSize: 32, fontWeight: 'bold', offsetCenter: [0, '65%'] },
      data: [{ value: score }],
    }],
  })
}

function resizeAll() { scoreChart?.resize() }

onMounted(async () => {
  await store.fetchEvaluation()
  await store.fetchCertProgress()
  await nextTick()
  initScoreChart()
  window.addEventListener('resize', resizeAll)
})

watch(() => store.evaluation.indicators, () => { nextTick(() => initScoreChart()) })

onUnmounted(() => {
  window.removeEventListener('resize', resizeAll)
  scoreChart?.dispose()
})
</script>

<style scoped>
.evaluation-page { padding: 4px; }
.page-header h3 { margin: 0; font-size: 18px; color: #303133; }
.grade-badge { font-size: 48px; font-weight: bold; }
</style>