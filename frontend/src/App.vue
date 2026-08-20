<template>
  <div id="app-container">
    <el-container>
      <!-- 侧边栏 -->
      <el-aside width="220px">
        <div class="logo">
          <span class="logo-icon">⚡</span>
          <span class="logo-text">zero_carbon_park_agent</span>
        </div>
        <el-menu
          :default-active="activeMenu"
          router
          background-color="transparent"
          text-color="#ffffffb3"
          active-text-color="#4FC3F7"
        >
          <el-menu-item index="/">
            <span>📊 驾驶舱大屏</span>
          </el-menu-item>
          <el-menu-item index="/park">
            <span>🏗️ 园区智能监测</span>
          </el-menu-item>
          <el-menu-item index="/water">
            <span>💧 水质监测</span>
          </el-menu-item>
          <el-menu-item index="/carbon">
            <span>🌿 碳足迹追踪</span>
          </el-menu-item>
          <el-menu-item index="/graph">
            <span>🔗 知识图谱</span>
          </el-menu-item>
          <el-menu-item index="/alert">
            <span>🚨 告警中心</span>
          </el-menu-item>
          <el-menu-item index="/agent">
            <span>🤖 Agent 工作流</span>
          </el-menu-item>
          <el-divider style="border-color:rgba(255,255,255,0.15);margin:8px 0" />
          <el-menu-item index="/energy">
            <span>⚡ 能源调度</span>
          </el-menu-item>
          <el-menu-item index="/storage">
            <span>🔋 储能管理</span>
          </el-menu-item>
          <el-menu-item index="/vpp">
            <span>🏭 虚拟电厂</span>
          </el-menu-item>
          <el-menu-item index="/carbon-asset">
            <el-tooltip content="碳资产管理" placement="right">
              <span>💰 碳资产管理</span>
            </el-tooltip>
          </el-menu-item>
          <el-menu-item index="/evaluation">
            <span>📋 零碳评价</span>
          </el-menu-item>
          <el-menu-item index="/economic">
            <span>📈 经济性分析</span>
          </el-menu-item>
          <el-menu-item index="/biomass">
            <span>🌱 生物质能</span>
          </el-menu-item>
        </el-menu>
        <div class="sidebar-version">v1.0.0</div>
      </el-aside>

      <!-- 主内容 -->
      <el-container>
        <el-header>
          <h2>零碳园区智慧能源与水务智能体系统</h2>
          <div class="header-right">
            <el-tag :type="store.llmConfigured ? 'success' : 'warning'" size="small">
              {{ store.llmConfigured ? 'LLM 已连接' : 'LLM 模拟模式' }}
            </el-tag>
          </div>
        </el-header>
        <el-main>
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useApiStore } from './stores/api'

const route = useRoute()
const store = useApiStore()
const activeMenu = computed(() => route.path)

onMounted(() => store.checkHealth())
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Microsoft YaHei', sans-serif; background: #f0f2f5; }
#app-container { height: 100vh; }

.el-aside {
  background: linear-gradient(180deg, #001529 0%, #002140 50%, #001529 100%);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.logo {
  padding: 20px 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  background: linear-gradient(135deg, rgba(79,195,247,0.2) 0%, rgba(0,21,41,0) 100%);
  border-bottom: 1px solid rgba(255,255,255,0.08);
}
.logo-icon { font-size: 22px; flex-shrink: 0; }
.logo-text {
  color: #fff;
  font-size: 12px;
  font-weight: bold;
  letter-spacing: 0.5px;
  word-break: break-all;
  line-height: 1.4;
}

.sidebar-version {
  margin-top: auto;
  padding: 12px 16px;
  color: rgba(255,255,255,0.3);
  font-size: 12px;
  text-align: center;
  border-top: 1px solid rgba(255,255,255,0.08);
}

.el-header {
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  z-index: 10;
}
.el-header h2 {
  font-size: 18px;
  color: #303133;
}

.el-main {
  padding: 20px;
  overflow-y: auto;
}

.el-menu {
  border-right: none;
  flex: 1;
  overflow-y: auto;
}
.el-menu .el-menu-item:hover {
  background-color: rgba(255,255,255,0.06) !important;
}
</style>