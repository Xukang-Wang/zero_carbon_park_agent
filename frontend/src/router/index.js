import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import WaterMonitor from '../views/WaterMonitor.vue'
import CarbonTracker from '../views/CarbonTracker.vue'
import GraphView from '../views/GraphView.vue'
import AlertCenter from '../views/AlertCenter.vue'
import AgentWorkflow from '../views/AgentWorkflow.vue'
import EnergyView from '../views/EnergyView.vue'
import StorageView from '../views/StorageView.vue'
import VPPView from '../views/VPPView.vue'
import CarbonAssetView from '../views/CarbonAssetView.vue'
import EvaluationView from '../views/EvaluationView.vue'
import EconomicView from '../views/EconomicView.vue'
import BiomassView from '../views/BiomassView.vue'
import ParkMonitor from '../views/ParkMonitor.vue'

const routes = [
  { path: '/', component: Dashboard },
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
})