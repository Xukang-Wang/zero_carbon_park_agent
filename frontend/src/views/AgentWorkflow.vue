<template>
  <div class="agent-workflow">
    <el-card shadow="hover">
      <template #header><span>Agent 工作流控制台</span></template>

      <el-row :gutter="20">
        <el-col :span="8">
          <el-card shadow="never" class="trigger-card">
            <h3>触发工作流</h3>
            <el-form label-width="100px">
              <el-form-item label="工作流类型">
                <el-select v-model="workflowType" style="width:100%">
                  <el-option label="水质异常处置" value="water_anomaly" />
                  <el-option label="日报生成" value="daily_report" />
                </el-select>
              </el-form-item>
              <el-form-item label="设备编号">
                <el-input v-model="wfParams.device_id" placeholder="WQ-001" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="handleTrigger" :loading="store.workflow.triggering || workflowRunning">
                  {{ workflowRunning ? '执行中...' : '启动工作流' }}
                </el-button>
              </el-form-item>
            </el-form>

            <!-- 工作流步骤说明 -->
            <el-divider />
            <h4>工作流步骤</h4>
            <el-steps direction="vertical" :active="currentStep" finish-status="success">
              <el-step title="异常检测" description="调用预测工具，检测水质异常" />
              <el-step title="根因分析" description="知识图谱追溯，定位异常源头" />
              <el-step title="调度决策" description="生成处置方案，评估碳影响" />
              <el-step title="任务派发" description="创建工单，推送通知" />
              <el-step title="报告生成" description="自动生成Markdown处置报告" />
            </el-steps>
          </el-card>
        </el-col>

        <el-col :span="16">
          <el-card shadow="never">
            <h3>工作流执行状态</h3>
            <div v-if="store.workflow.current" style="margin-top:16px">
              <el-descriptions :column="2" border>
                <el-descriptions-item label="工作流ID">{{ store.workflow.current.workflow_id }}</el-descriptions-item>
                <el-descriptions-item label="类型">{{ store.workflow.current.workflow_type }}</el-descriptions-item>
                <el-descriptions-item label="状态">
                  <el-tag :type="statusTagType">{{ store.workflow.current.status }}</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="启动时间">{{ store.workflow.current.started_at }}</el-descriptions-item>
              </el-descriptions>

              <div v-if="store.workflow.report" style="margin-top:20px">
                <h4>处置报告</h4>
                <div class="report-content" v-html="renderedReport"></div>
              </div>
            </div>
            <el-empty v-else description='点击"启动工作流"开始' />
          </el-card>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useApiStore } from '../stores/api'
import { ElMessage } from 'element-plus'

const store = useApiStore()
const workflowType = ref('water_anomaly')
const wfParams = ref({ device_id: 'WQ-001' })
const workflowRunning = ref(false)

const currentStep = computed(() => {
  const s = store.workflow.current?.current_step
  const steps = { anomaly_detection: 0, root_cause_analysis: 1, dispatch_decision: 2, task_assignment: 3, report_generation: 4 }
  return steps[s] ?? 0
})

const statusTagType = computed(() => {
  const s = store.workflow.current?.status
  if (s === 'completed') return 'success'
  if (s === 'failed') return 'danger'
  return 'warning'
})

const renderedReport = computed(() => {
  const r = store.workflow.report
  if (!r) return ''
  return r
    .replace(/\n/g, '<br>')
    .replace(/^### (.*$)/gm, '<h4>$1</h4>')
    .replace(/^## (.*$)/gm, '<h3>$1</h3>')
    .replace(/^# (.*$)/gm, '<h2>$1</h2>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/^- (.*$)/gm, '<li>$1</li>')
})

async function handleTrigger() {
  try {
    workflowRunning.value = true
    const data = await store.triggerWorkflow(workflowType.value, wfParams.value)
    ElMessage.success('工作流已启动')

    // 轮询状态
    let attempts = 0
    const interval = setInterval(async () => {
      const status = await store.pollWorkflowStatus(data.workflow_id)
      if (status?.status === 'completed' || status?.status === 'failed' || ++attempts > 30) {
        clearInterval(interval)
        workflowRunning.value = false
      }
    }, 2000)
  } catch {
    ElMessage.error('工作流启动失败')
    workflowRunning.value = false
  }
}
</script>

<style scoped>
.trigger-card { background: #fafafa; }
.report-content {
  background: #f5f7fa;
  padding: 20px;
  border-radius: 8px;
  line-height: 1.8;
  max-height: 500px;
  overflow-y: auto;
  font-size: 14px;
}
.report-content :deep(h2) { font-size: 18px; margin: 16px 0 8px; color: #303133; }
.report-content :deep(h3) { font-size: 16px; margin: 12px 0 6px; color: #303133; }
.report-content :deep(h4) { font-size: 14px; margin: 10px 0 4px; color: #606266; }
.report-content :deep(li) { margin-left: 20px; }
.report-content :deep(strong) { color: #303133; }
</style>