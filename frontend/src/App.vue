<template>
  <div class="app-shell">
    <aside class="app-sidebar">
      <router-link to="/" class="brand"><span class="brand-symbol">◈</span><span>青屿 · ZERO<span class="brand-caption">CARBON INTELLIGENCE</span></span></router-link>
      <div class="workspace-label">园区智能运营平台 <span>V2.0</span></div>
      <nav aria-label="主导航">
        <p class="nav-section">工作空间</p>
        <router-link v-for="item in primary" :key="item.path" :to="item.path" :class="['nav-link', { active: route.path === item.path }]" ><span class="nav-icon">{{ item.icon }}</span>{{ item.label }}<span v-if="item.path === '/agents'" class="nav-count">07</span></router-link>
        <p class="nav-section">专业应用</p>
        <router-link v-for="item in specialist" :key="item.path" :to="item.path" :class="['nav-link', { active: route.path === item.path }]" ><span class="nav-icon">{{ item.icon }}</span>{{ item.label }}</router-link>
      </nav>
      <div class="sidebar-bottom"><span class="status-dot"></span> 本地模拟环境 <span class="small-muted">DEMO</span><p>让每一度能源，都有迹可循。</p></div>
    </aside>
    <div class="app-body">
      <header class="app-topbar"><div><span class="small-muted">WORKSPACE</span><span class="breadcrumb">青屿示范园区 <span>/</span> {{ title }}</span></div><div class="topbar-right"><span class="demo-chip">模拟数据</span><span class="user-avatar">QY</span></div></header>
      <main class="app-main"><router-view /></main>
    </div>
  </div>
</template>
<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import './styles/operations.css'
const route = useRoute()
const primary = [{ path: '/', label: '园区总览', icon: '◫' }, { path: '/agents', label: 'Agent 协作中心', icon: '⌘' }, { path: '/scenarios', label: '策略推演', icon: '◇' }, { path: '/carbon-analysis', label: '碳与资源分析', icon: '◌' }, { path: '/data-center', label: '数据与资产', icon: '▤' }]
const specialist = [{ path: '/park', label: '综合能源监测', icon: '⌁' }, { path: '/energy', label: '能源调度', icon: 'ϟ' }, { path: '/storage', label: '储能管理', icon: '▱' }, { path: '/vpp', label: '虚拟电厂', icon: '⌂' }, { path: '/water', label: '水务监测', icon: '≈' }, { path: '/graph', label: '能源知识图谱', icon: '⋈' }, { path: '/alert', label: '告警中心', icon: '△' }, { path: '/carbon', label: '碳足迹追踪', icon: '♧' }, { path: '/carbon-asset', label: '碳资产管理', icon: '◎' }, { path: '/economic', label: '项目经济性', icon: '↗' }, { path: '/evaluation', label: '零碳评价', icon: '▧' }, { path: '/biomass', label: '生物质能', icon: '♧' }, { path: '/agent', label: '经典工作流', icon: '⇢' }]
const title = computed(() => [...primary, ...specialist].find(i => i.path === route.path)?.label || '工作台')
</script>
