<template>
  <div class="agent-network">
    <svg viewBox="0 0 1080 420" aria-label="Agent 依赖与执行状态图">
      <defs><pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="#253c3d" /></pattern></defs>
      <rect width="1080" height="420" fill="url(#dots)" />
      <g v-for="edge in edges" :key="edge.source + edge.target">
        <path :d="path(edge)" fill="none" :stroke="status(edge.source) === 'completed' ? '#5ce4bb' : '#304849'" stroke-width="1.5" :class="{ 'flow-path': status(edge.target) === 'running' }" />
        <circle v-if="status(edge.target) === 'running'" r="4" fill="#bbffde"><animateMotion :path="path(edge)" dur="1.4s" repeatCount="indefinite" /></circle>
      </g>
      <g v-for="(node, index) in nodes" :key="node.id" :transform="`translate(${node.x},${node.y})`" class="agent-node" tabindex="0" role="button" :aria-label="node.name + '，' + statusLabel(status(node.id))" @click="$emit('select', node.id)" @keydown.enter="$emit('select', node.id)" @keydown.space.prevent="$emit('select', node.id)">
        <circle v-if="status(node.id) === 'running'" r="42" fill="#55deb51c" class="node-pulse" />
        <rect x="-72" y="-35" width="144" height="88" rx="13" :fill="selected === node.id ? '#193e35' : '#102527'" :stroke="status(node.id) === 'completed' ? '#4bbb98' : status(node.id) === 'failed' ? '#f09883' : status(node.id) === 'running' ? '#c8f7ab' : '#355050'" />
        <text x="-55" y="-12" fill="#7da09b" font-size="10" font-family="monospace">AGENT / 0{{ index + 1 }}</text>
        <circle cx="53" cy="-16" r="3" :fill="status(node.id) === 'completed' ? '#5ce4bb' : '#839994'" />
        <text text-anchor="middle" y="11" fill="#edf6f0" font-size="15">{{ node.name }}</text>
        <text text-anchor="middle" y="35" fill="#8fa9a3" font-size="10">{{ statusLabel(status(node.id)) }}</text>
      </g>
    </svg>
  </div>
</template>
<script setup>
const props = defineProps({ nodes: { type: Array, default: () => [] }, edges: { type: Array, default: () => [] }, states: { type: Object, default: () => ({}) }, selected: String })
defineEmits(['select'])
const status = id => props.states[id] || 'idle'
const statusLabel = state => ({ idle: '等待依赖', running: '正在计算', completed: '证据已就绪', failed: '执行失败', skipped: '上游失败 · 跳过' })[state]
function path(edge) {
  const a = props.nodes.find(n => n.id === edge.source), b = props.nodes.find(n => n.id === edge.target)
  if (!a || !b) return ''
  return `M ${a.x + 72} ${a.y + 8} C ${(a.x + b.x) / 2} ${a.y + 8}, ${(a.x + b.x) / 2} ${b.y + 8}, ${b.x - 72} ${b.y + 8}`
}
</script>
<style scoped>
.agent-network svg { width: 100%; display: block; min-height: 240px; }.agent-node { cursor: pointer; outline: none; }.agent-node:focus rect { stroke: #fff; stroke-width: 3; }.agent-node:hover rect { fill: #204239; }.flow-path { stroke-dasharray: 6 7; animation: flow 1s linear infinite; }.node-pulse { animation: pulse 1s ease-in-out infinite alternate; }@keyframes flow { to { stroke-dashoffset: -26; } }@keyframes pulse { to { opacity: .25; } }@media(prefers-reduced-motion: reduce) { * { animation: none !important; } }
</style>
