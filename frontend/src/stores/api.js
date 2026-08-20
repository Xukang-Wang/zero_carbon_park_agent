/**
 * zero_carbon_park_agent 前端数据存储 —— Pinia Store
 * 统一管理所有 API 数据请求、缓存与状态
 */
import { defineStore } from 'pinia'
import axios from 'axios'

const api = axios.create({ baseURL: '/api/v1', timeout: 10000 })

export const useApiStore = defineStore('api', {
  state: () => ({
    // 驾驶舱
    dashboard: {
      cards: { solar_kw: null, total_load_kw: null, carbon_tco2: null, battery_soc: null },
      loading: false,
      error: null,
    },
    // 水质数据
    water: {
      history: [],
      predictions: null,
      anomalyFlags: [],
      loading: false,
      predicting: false,
      error: null,
    },
    // 碳足迹
    carbon: {
      footprint: null,
      trend: [],
      loading: false,
      error: null,
    },
    // 知识图谱
    graph: {
      overview: null,
      traceResult: null,
      loading: false,
      error: null,
    },
    // 告警
    alerts: {
      events: [],
      loading: false,
      error: null,
    },
    // 工作流
    workflow: {
      current: null,
      report: null,
      triggering: false,
      polling: false,
      error: null,
    },
    // LLM 状态
    llmConfigured: false,
    // 能源管理
    energy: {
      dispatchStatus: null,
      powerForecast: null,
      pvForecast: null,
      windForecast: null,
      greenPowerTrace: null,
      loading: false,
      error: null,
    },
    // 储能管理
    storage: {
      status: null,
      optimizeResult: null,
      sharedStorage: null,
      loading: false,
      error: null,
    },
    // VPP
    vpp: {
      status: null,
      bidResult: null,
      resources: null,
      loading: false,
      error: null,
    },
    // 碳资产管理
    carbonAsset: {
      scopeEmissions: null,
      portfolio: null,
      tradingStrategy: null,
      cbamReport: null,
      loading: false,
      error: null,
    },
    // 零碳评价
    evaluation: {
      indicators: null,
      certProgress: null,
      loading: false,
      error: null,
    },
    // 经济性分析
    economic: {
      pvEconomics: null,
      storageEconomics: null,
      comprehensive: null,
      loading: false,
      error: null,
    },
    // 生物质能
    biomass: {
      chpAnalysis: null,
      biogasAnalysis: null,
      loading: false,
      error: null,
    },
    // 园区综合监控
    park: {
      snapshot: null,
      nodes: null,
      alerts: null,
      dispatchResult: null,
      powerFlow: null,
      hourlyTrend: [],
      vppAggregation: null,
      loading: false,
      error: null,
    },
  }),

  actions: {
    // ── 驾驶舱 ──
    async fetchDashboard() {
      this.dashboard.loading = true
      this.dashboard.error = null
      try {
        const [graphRes, carbonRes, alertRes] = await Promise.allSettled([
          api.get('/graph/overview'),
          api.get('/carbon/footprint'),
          api.get('/agent/anomaly/events?limit=5'),
        ])
        if (graphRes.status === 'fulfilled') {
          const d = graphRes.value.data.data
          this.dashboard.cards = {
            solar_kw: d?.total_renewable_capacity_kw ?? 5000,
            total_load_kw: d?.total_load_kw ?? 5800,
            carbon_tco2: null,
            battery_soc: d?.storage_soc ?? 72,
          }
        }
        if (carbonRes.status === 'fulfilled') {
          const c = carbonRes.value.data.data
          this.dashboard.cards.carbon_tco2 = c?.net_emission_tco2_per_h
            ? (c.net_emission_tco2_per_h * 24).toFixed(1)
            : null
        }
        if (alertRes.status === 'fulfilled') {
          this.alerts.events = (alertRes.value.data.data?.events || []).slice(0, 5)
        }
      } catch (e) {
        this.dashboard.error = e.message
      } finally {
        this.dashboard.loading = false
      }
    },

    // ── 水质 ──
    async fetchWaterHistory(deviceId = 'WQ-001', hours = 48) {
      this.water.loading = true
      this.water.error = null
      try {
        const res = await api.get('/water/history', { params: { device_id: deviceId, hours } })
        this.water.history = res.data.data?.records || []
      } catch (e) {
        this.water.error = e.message
      } finally {
        this.water.loading = false
      }
    },

    async predictWater(deviceId = 'WQ-001', horizon = 24) {
      this.water.predicting = true
      try {
        const res = await api.post('/water/predict', { device_id: deviceId, horizon_hours: horizon })
        this.water.predictions = res.data.data?.predictions || []
        this.water.anomalyFlags = res.data.data?.anomaly_flags || []
      } catch (e) {
        this.water.error = e.message
      } finally {
        this.water.predicting = false
      }
    },

    // ── 碳足迹 ──
    async fetchCarbon() {
      this.carbon.loading = true
      this.carbon.error = null
      try {
        const [footprintRes, trendRes] = await Promise.allSettled([
          api.get('/carbon/footprint'),
          api.get('/carbon/trend'),
        ])
        if (footprintRes.status === 'fulfilled') {
          this.carbon.footprint = footprintRes.value.data.data
        }
        if (trendRes.status === 'fulfilled') {
          this.carbon.trend = trendRes.value.data.data?.trend || []
        }
      } catch (e) {
        this.carbon.error = e.message
      } finally {
        this.carbon.loading = false
      }
    },

    // ── 图谱 ──
    async fetchGraphOverview() {
      this.graph.loading = true
      this.graph.error = null
      try {
        const res = await api.get('/graph/overview')
        this.graph.overview = res.data.data
      } catch (e) {
        this.graph.error = e.message
      } finally {
        this.graph.loading = false
      }
    },

    async traceEnergy(entityId, direction = 'upstream') {
      try {
        const res = await api.get('/graph/energy-trace', {
          params: { entity_id: entityId, trace_direction: direction },
        })
        this.graph.traceResult = res.data.data?.trace_path || []
      } catch (e) {
        this.graph.error = e.message
      }
    },

    // ── 告警 ──
    async fetchAlerts(limit = 50) {
      this.alerts.loading = true
      this.alerts.error = null
      try {
        const res = await api.get('/agent/anomaly/events', { params: { limit } })
        this.alerts.events = res.data.data?.events || []
      } catch (e) {
        this.alerts.error = e.message
      } finally {
        this.alerts.loading = false
      }
    },

    // ── 工作流 ──
    async triggerWorkflow(type, params) {
      this.workflow.triggering = true
      this.workflow.error = null
      try {
        const res = await api.post('/agent/workflow/trigger', {
          workflow_type: type,
          params,
        })
        this.workflow.current = res.data.data
        return res.data.data
      } catch (e) {
        this.workflow.error = e.message
        throw e
      } finally {
        this.workflow.triggering = false
      }
    },

    async pollWorkflowStatus(workflowId) {
      this.workflow.polling = true
      try {
        const res = await api.get(`/agent/workflow/${workflowId}/status`)
        this.workflow.current = res.data.data
        if (res.data.data?.has_report) {
          const reportRes = await api.get(`/agent/workflow/${workflowId}/report`)
          this.workflow.report = reportRes.data.data?.report
        }
        return res.data.data
      } catch (e) {
        this.workflow.error = e.message
      } finally {
        this.workflow.polling = false
      }
    },

    // ──健康检查 ──
    async checkHealth() {
      try {
        const res = await api.get('/health')
        this.llmConfigured = res.data?.llm_configured ?? false
      } catch {
        this.llmConfigured = false
      }
    },

    // ── 能源管理 ──
    async fetchEnergyDispatch() {
      this.energy.loading = true
      try {
        const res = await api.get('/energy/dispatch/status')
        this.energy.dispatchStatus = res.data.data
      } catch (e) {
        this.energy.error = e.message
      } finally {
        this.energy.loading = false
      }
    },

    async fetchPowerForecast(source = 'pv') {
      try {
        const res = await api.get('/energy/power-forecast', { params: { source } })
        if (source === 'wind') {
          this.energy.windForecast = res.data.data
        } else {
          this.energy.pvForecast = res.data.data
        }
      } catch (e) {
        this.energy.error = e.message
      }
    },

    async traceGreenPower(entityId) {
      try {
        const res = await api.get('/energy/green-power/trace', { params: { entity_id: entityId } })
        this.energy.greenPowerTrace = res.data.data
      } catch (e) {
        this.energy.error = e.message
      }
    },

    // ── 储能管理 ──
    async fetchStorageStatus() {
      this.storage.loading = true
      try {
        const res = await api.get('/storage/status')
        this.storage.status = res.data.data
      } catch (e) {
        this.storage.error = e.message
      } finally {
        this.storage.loading = false
      }
    },

    async optimizeStorage(params = {}) {
      try {
        const res = await api.post('/storage/optimize', params)
        this.storage.optimizeResult = res.data.data
      } catch (e) {
        this.storage.error = e.message
      }
    },

    async fetchSharedStorage() {
      try {
        const res = await api.get('/storage/shared-storage/analysis')
        this.storage.sharedStorage = res.data.data
      } catch (e) {
        this.storage.error = e.message
      }
    },

    // ── VPP ──
    async fetchVPPStatus() {
      this.vpp.loading = true
      try {
        const res = await api.get('/vpp/status')
        this.vpp.status = res.data.data
      } catch (e) {
        this.vpp.error = e.message
      } finally {
        this.vpp.loading = false
      }
    },

    async submitVPPBid(params = {}) {
      try {
        const res = await api.post('/vpp/bid', params)
        this.vpp.bidResult = res.data.data
      } catch (e) {
        this.vpp.error = e.message
      }
    },

    async fetchVPPResources() {
      try {
        const res = await api.get('/vpp/resources')
        this.vpp.resources = res.data.data
      } catch (e) {
        this.vpp.error = e.message
      }
    },

    // ── 碳资产管理 ──
    async fetchScopeEmissions() {
      this.carbonAsset.loading = true
      try {
        const res = await api.get('/carbon-asset/emissions')
        this.carbonAsset.scopeEmissions = res.data.data
      } catch (e) {
        this.carbonAsset.error = e.message
      } finally {
        this.carbonAsset.loading = false
      }
    },

    async fetchCarbonPortfolio() {
      try {
        const res = await api.get('/carbon-asset/portfolio')
        this.carbonAsset.portfolio = res.data.data
      } catch (e) {
        this.carbonAsset.error = e.message
      }
    },

    async fetchTradingStrategy() {
      try {
        const res = await api.get('/carbon-asset/trading-strategy')
        this.carbonAsset.tradingStrategy = res.data.data
      } catch (e) {
        this.carbonAsset.error = e.message
      }
    },

    async fetchCBAMReport(productType = 'steel') {
      try {
        const res = await api.get('/carbon-asset/cbam-report', { params: { product_type: productType } })
        this.carbonAsset.cbamReport = res.data.data
      } catch (e) {
        this.carbonAsset.error = e.message
      }
    },

    // ── 零碳评价 ──
    async fetchEvaluation() {
      this.evaluation.loading = true
      try {
        const res = await api.get('/evaluation/indicators')
        this.evaluation.indicators = res.data.data
      } catch (e) {
        this.evaluation.error = e.message
      } finally {
        this.evaluation.loading = false
      }
    },

    async fetchCertProgress() {
      try {
        const res = await api.get('/evaluation/certification-progress')
        this.evaluation.certProgress = res.data.data
      } catch (e) {
        this.evaluation.error = e.message
      }
    },

    // ── 经济性分析 ──
    async fetchPVEconomics() {
      this.economic.loading = true
      try {
        const res = await api.get('/economic/pv-economics')
        this.economic.pvEconomics = res.data.data
      } catch (e) {
        this.economic.error = e.message
      } finally {
        this.economic.loading = false
      }
    },

    async fetchStorageEconomics() {
      try {
        const res = await api.get('/economic/storage-economics')
        this.economic.storageEconomics = res.data.data
      } catch (e) {
        this.economic.error = e.message
      }
    },

    async fetchComprehensiveEconomics() {
      try {
        const res = await api.get('/economic/comprehensive')
        this.economic.comprehensive = res.data.data
      } catch (e) {
        this.economic.error = e.message
      }
    },

    // ── 生物质能 ──
    async fetchCHPAnalysis() {
      this.biomass.loading = true
      try {
        const res = await api.get('/biomass/chp-analysis')
        this.biomass.chpAnalysis = res.data.data
      } catch (e) {
        this.biomass.error = e.message
      } finally {
        this.biomass.loading = false
      }
    },

    async fetchBiogasAnalysis() {
      try {
        const res = await api.get('/biomass/biogas-analysis')
        this.biomass.biogasAnalysis = res.data.data
      } catch (e) {
        this.biomass.error = e.message
      }
    },

    // ── 园区综合监控 ──
    async fetchParkSnapshot() {
      this.park.loading = true
      try {
        const res = await api.get('/park/snapshot')
        this.park.snapshot = res.data.data
      } catch (e) {
        this.park.error = e.message
      } finally {
        this.park.loading = false
      }
    },

    async fetchParkNodes() {
      try {
        const res = await api.get('/park/nodes')
        this.park.nodes = res.data.data
      } catch (e) {
        this.park.error = e.message
      }
    },

    async fetchParkAlerts() {
      try {
        const res = await api.get('/park/alerts')
        this.park.alerts = res.data.data
      } catch (e) {
        this.park.error = e.message
      }
    },

    async optimizeDispatch(strategy = 'balanced') {
      try {
        const res = await api.post('/park/dispatch/optimize', { strategy })
        this.park.dispatchResult = res.data.data
      } catch (e) {
        this.park.error = e.message
      }
    },

    async fetchPowerFlow() {
      try {
        const res = await api.get('/park/power-flow')
        this.park.powerFlow = res.data.data
      } catch (e) {
        this.park.error = e.message
      }
    },

    async fetchHourlyTrend(hours = 24) {
      try {
        const res = await api.get('/park/trend/hourly', { params: { hours } })
        this.park.hourlyTrend = res.data.data?.trend || []
      } catch (e) {
        this.park.error = e.message
      }
    },

    async fetchVPPAggregation() {
      try {
        const res = await api.get('/park/vpp/aggregation')
        this.park.vppAggregation = res.data.data
      } catch (e) {
        this.park.error = e.message
      }
    },
  },
})