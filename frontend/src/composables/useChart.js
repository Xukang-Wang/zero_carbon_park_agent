/**
 * zero_carbon_park_agent 图表 composable
 * 统一 ECharts 初始化、resize、销毁逻辑，支持多实例
 */
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'

export function useChart(optionFactory, theme = null) {
  const container = ref(null)
  let instance = null
  let resizeObserver = null
  let isLoading = ref(false)

  function init() {
    if (!container.value) return
    instance = echarts.init(container.value, theme)
    instance.setOption(optionFactory())
    // 使用 ResizeObserver 自动监听容器尺寸变化
    if (window.ResizeObserver) {
      resizeObserver = new ResizeObserver(() => {
        instance?.resize()
      })
      resizeObserver.observe(container.value)
    }
  }

  function update() {
    if (!instance) return
    instance.setOption(optionFactory(), { notMerge: true })
  }

  function resize() {
    instance?.resize()
  }

  function dispose() {
    instance?.dispose()
    instance = null
    if (resizeObserver) {
      resizeObserver.disconnect()
      resizeObserver = null
    }
  }

  function getInstance() {
    return instance
  }

  function setLoading(loading) {
    isLoading.value = loading
    if (instance) {
      if (loading) {
        instance.showLoading({ text: '加载中...', color: '#409EFF', maskColor: 'rgba(255,255,255,0.8)' })
      } else {
        instance.hideLoading()
      }
    }
  }

  onMounted(async () => {
    await nextTick()
    init()
    window.addEventListener('resize', resize)
  })

  onUnmounted(() => {
    window.removeEventListener('resize', resize)
    if (resizeObserver) {
      resizeObserver.disconnect()
      resizeObserver = null
    }
    dispose()
  })

  return { container, init, update, resize, dispose, getInstance, setLoading, isLoading }
}