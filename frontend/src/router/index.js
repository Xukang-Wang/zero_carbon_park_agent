import { createRouter, createWebHistory } from 'vue-router'
import OperationsCenter from '../views/OperationsCenter.vue'
const WaterMonitor = () => import('../views/WaterMonitor.vue')
const CarbonTracker = () => import('../views/CarbonTracker.vue')
const GraphView = () => import('../views/GraphView.vue')
const AlertCenter = () => import('../views/AlertCenter.vue')
const AgentWorkflow = () => import('../views/AgentWorkflow.vue')
const EnergyView = () => import('../views/EnergyView.vue')
const StorageView = () => import('../views/StorageView.vue')
const VPPView = () => import('../views/VPPView.vue')
const CarbonAssetView = () => import('../views/CarbonAssetView.vue')
const EvaluationView = () => import('../views/EvaluationView.vue')
const EconomicView = () => import('../views/EconomicView.vue')
const BiomassView = () => import('../views/BiomassView.vue')
const ParkMonitor = () => import('../views/ParkMonitor.vue')

const routes = [
  { path: '/', component: OperationsCenter },
  { path: '/agents', component: OperationsCenter },
  { path: '/scenarios', component: OperationsCenter },
  { path: '/carbon-analysis', component: OperationsCenter },
  { path: '/data-center', component: OperationsCenter },
  { path: '/water', component: WaterMonitor },
  { path: '/carbon', component: CarbonTracker },
  { path: '/graph', component: GraphView },
  { path: '/alert', component: AlertCenter },
  { path: '/agent', component: AgentWorkflow },
  { path: '/energy', component: EnergyView },
  { path: '/storage', component: StorageView },
  { path: '/vpp', component: VPPView },
  { path: '/carbon-asset', component: CarbonAssetView },
  { path: '/evaluation', component: EvaluationView },
  { path: '/economic', component: EconomicView },
  { path: '/biomass', component: BiomassView },
  { path: '/park', component: ParkMonitor },
]

export default createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})
