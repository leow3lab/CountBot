<template>
  <div class="evermemos-config">
    <!-- 标题 -->
    <div class="section-header">
      <h3 class="section-title">{{ $t('settings.evermemos.title') }}</h3>
      <p class="section-desc">{{ $t('settings.evermemos.description') }}</p>
    </div>

    <!-- 启用开关 -->
    <div class="form-group">
      <div class="toggle-row">
        <div class="toggle-info">
          <label class="label">{{ $t('settings.evermemos.enable') }}</label>
          <p class="hint-text">{{ $t('settings.evermemos.enableHint') }}</p>
        </div>
        <label class="toggle-switch">
          <input type="checkbox" v-model="cfg.enabled" @change="syncToStore" />
          <span class="toggle-slider"></span>
        </label>
      </div>
    </div>

    <!-- 以下字段在未启用时置灰 -->
    <div :class="{ 'disabled-section': !cfg.enabled }">

      <!-- API 地址 -->
      <div class="form-group">
        <label class="label">{{ $t('settings.evermemos.apiBaseUrl') }}</label>
        <div class="input-with-action">
          <Input
            v-model="cfg.api_base_url"
            type="text"
            :placeholder="$t('settings.evermemos.apiBaseUrlPlaceholder')"
            :disabled="!cfg.enabled"
            @blur="syncToStore"
          />
          <Button
            variant="secondary"
            :loading="testing"
            :disabled="!cfg.enabled"
            @click="testConnection"
          >
            {{ testing ? $t('common.testing') : $t('common.test') }}
          </Button>
        </div>
        <!-- 健康状态指示 -->
        <div v-if="healthStatus !== null" class="health-status" :class="healthStatus ? 'healthy' : 'unhealthy'">
          <span class="health-dot"></span>
          <span>{{ healthStatus ? $t('settings.evermemos.connected') : $t('settings.evermemos.disconnected') }}</span>
        </div>
      </div>

      <!-- 用户 ID -->
      <div class="form-group">
        <label class="label">{{ $t('settings.evermemos.userId') }}</label>
        <Input
          v-model="cfg.user_id"
          type="text"
          :placeholder="$t('settings.evermemos.userIdPlaceholder')"
          :disabled="!cfg.enabled"
          @blur="syncToStore"
        />
        <p class="hint-text">{{ $t('settings.evermemos.userIdHint') }}</p>
      </div>

      <!-- 群组 ID（可选） -->
      <div class="form-group">
        <label class="label">{{ $t('settings.evermemos.groupId') }} <span class="optional-tag">{{ $t('common.optional') }}</span></label>
        <Input
          v-model="cfg.group_id"
          type="text"
          :placeholder="$t('settings.evermemos.groupIdPlaceholder')"
          :disabled="!cfg.enabled"
          @blur="syncToStore"
        />
        <p class="hint-text">{{ $t('settings.evermemos.groupIdHint') }}</p>
      </div>

      <!-- 自动写入记忆 -->
      <div class="form-group">
        <div class="toggle-row">
          <div class="toggle-info">
            <label class="label">{{ $t('settings.evermemos.autoMemorize') }}</label>
            <p class="hint-text">{{ $t('settings.evermemos.autoMemorizeHint') }}</p>
          </div>
          <label class="toggle-switch">
            <input type="checkbox" v-model="cfg.auto_memorize" :disabled="!cfg.enabled" @change="syncToStore" />
            <span class="toggle-slider"></span>
          </label>
        </div>
      </div>

      <!-- 自动注入记忆 -->
      <div class="form-group">
        <div class="toggle-row">
          <div class="toggle-info">
            <label class="label">{{ $t('settings.evermemos.injectMemories') }}</label>
            <p class="hint-text">{{ $t('settings.evermemos.injectMemoriesHint') }}</p>
          </div>
          <label class="toggle-switch">
            <input type="checkbox" v-model="cfg.inject_memories" :disabled="!cfg.enabled" @change="syncToStore" />
            <span class="toggle-slider"></span>
          </label>
        </div>
      </div>

      <!-- 注入记忆条数 -->
      <div class="form-group">
        <label class="label">{{ $t('settings.evermemos.retrievalLimit') }}</label>
        <div class="number-input-row">
          <input
            v-model.number="cfg.retrieval_limit"
            type="number"
            min="1"
            max="20"
            step="1"
            class="number-input"
            :disabled="!cfg.enabled || !cfg.inject_memories"
            @blur="syncToStore"
          />
          <span class="unit-label">{{ $t('settings.evermemos.retrievalLimitUnit') }}</span>
        </div>
        <p class="hint-text">{{ $t('settings.evermemos.retrievalLimitHint') }}</p>
      </div>

      <!-- 检索模式 -->
      <div class="form-group">
        <label class="label">{{ $t('settings.evermemos.retrievalMode') }}</label>
        <select
          v-model="cfg.retrieval_mode"
          class="select-input"
          :disabled="!cfg.enabled || !cfg.inject_memories"
          @change="syncToStore"
        >
          <option value="agentic">{{ $t('settings.evermemos.modes.agentic') }}</option>
          <option value="hybrid">{{ $t('settings.evermemos.modes.hybrid') }}</option>
          <option value="vector">{{ $t('settings.evermemos.modes.vector') }}</option>
          <option value="keyword">{{ $t('settings.evermemos.modes.keyword') }}</option>
        </select>
        <p class="hint-text">{{ $t('settings.evermemos.retrievalModeHint') }}</p>
      </div>

      <!-- 请求超时 -->
      <div class="form-group">
        <label class="label">{{ $t('settings.evermemos.timeout') }}</label>
        <div class="number-input-row">
          <input
            v-model.number="cfg.timeout"
            type="number"
            min="1"
            max="60"
            step="1"
            class="number-input"
            :disabled="!cfg.enabled"
            @blur="syncToStore"
          />
          <span class="unit-label">{{ $t('settings.evermemos.timeoutUnit') }}</span>
        </div>
      </div>

      <!-- 记忆预览 -->
      <div v-if="cfg.enabled" class="form-group">
        <div class="preview-header">
          <label class="label">{{ $t('settings.evermemos.memoryPreview') }}</label>
          <div class="preview-actions">
            <div class="view-mode-switch">
              <button
                class="view-mode-btn"
                :class="{ active: previewViewMode === 'timeline' }"
                @click="previewViewMode = 'timeline'"
              >
                时间轴
              </button>
              <button
                class="view-mode-btn"
                :class="{ active: previewViewMode === 'list' }"
                @click="previewViewMode = 'list'"
              >
                列表
              </button>
            </div>
            <Button
              variant="secondary"
              size="sm"
              :loading="previewLoading"
              :disabled="!cfg.enabled"
              @click="loadMemoryPreview"
            >
              {{ $t('common.refresh') }}
            </Button>
          </div>
        </div>
        <div class="memory-preview-box">
          <div v-if="previewLoading" class="preview-loading">{{ $t('common.loading') }}</div>
          <div v-else-if="previewError" class="preview-error">{{ previewError }}</div>
          <div v-else-if="previewMemories.length === 0" class="preview-empty">
            {{ $t('settings.evermemos.noMemories') }}
          </div>
          <div v-else-if="previewViewMode === 'list'" class="preview-list">
            <div
              v-for="(mem, idx) in previewMemories"
              :key="idx"
              class="preview-item"
            >
              <span class="mem-index">{{ idx + 1 }}.</span>
              <div class="mem-main">
                <span class="mem-content">{{ getMemoryContent(mem) }}</span>
                <div class="mem-meta-row">
                  <span v-if="mem.memory_type" class="mem-type-badge">{{ getMemoryTypeLabel(mem.memory_type) }}</span>
                  <span class="mem-time">{{ formatMemoryTime(mem) }}</span>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="timeline-list">
            <div
              v-for="(mem, idx) in timelineMemories"
              :key="`tl-${idx}`"
              class="timeline-item"
            >
              <div class="timeline-dot"></div>
              <div class="timeline-content">
                <div class="timeline-time">{{ formatMemoryTime(mem) }}</div>
                <div class="timeline-text">{{ getMemoryContent(mem) }}</div>
                <div class="mem-meta-row">
                  <span v-if="mem.memory_type" class="mem-type-badge">{{ getMemoryTypeLabel(mem.memory_type) }}</span>
                  <span v-if="mem.group_id" class="mem-group">group: {{ mem.group_id }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

    </div><!-- end disabled-section -->
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Input from '@/components/ui/Input.vue'
import Button from '@/components/ui/Button.vue'
import { useSettingsStore } from '@/store/settings'
import { useToast } from '@/composables/useToast'
import { everMemosAPI } from '@/api'

const { t } = useI18n()
const settingsStore = useSettingsStore()
const toast = useToast()

// ── 本地配置状态 ───────────────────────────────────────────────────────────
const cfg = ref({
  enabled: false,
  api_base_url: 'http://localhost:1995',
  user_id: 'countbot_user',
  group_id: '',
  auto_memorize: true,
  inject_memories: true,
  retrieval_limit: 5,
  retrieval_mode: 'agentic',
  timeout: 10,
})

const isUpdating = ref(false)
const testing = ref(false)
const healthStatus = ref<boolean | null>(null)
const previewLoading = ref(false)
const previewError = ref('')
const previewMemories = ref<any[]>([])
const previewViewMode = ref<'list' | 'timeline'>('timeline')

// ── 初始化 ─────────────────────────────────────────────────────────────────
onMounted(async () => {
  await loadConfig()
  if (cfg.value.enabled) {
    await loadMemoryPreview()
  }
})

async function loadConfig() {
  try {
    const data = await everMemosAPI.getConfig()
    isUpdating.value = true
    Object.assign(cfg.value, data)
    isUpdating.value = false
  } catch {
    // 使用 store 中的数据降级
    if (settingsStore.settings?.evermemos) {
      isUpdating.value = true
      Object.assign(cfg.value, settingsStore.settings.evermemos)
      isUpdating.value = false
    }
  }
}

// ── 同步到 Store（父组件统一保存）───────────────────────────────────────────
function syncToStore() {
  if (!isUpdating.value && settingsStore.settings) {
    if (!settingsStore.settings.evermemos) {
      settingsStore.settings.evermemos = { ...cfg.value }
    } else {
      Object.assign(settingsStore.settings.evermemos, cfg.value)
    }
  }
}

// 监听 store 外部变更
watch(() => settingsStore.settings?.evermemos, (newCfg) => {
  if (newCfg && !isUpdating.value) {
    isUpdating.value = true
    Object.assign(cfg.value, newCfg)
    isUpdating.value = false
  }
}, { deep: true })

// ── 测试连接 ───────────────────────────────────────────────────────────────
async function testConnection() {
  testing.value = true
  healthStatus.value = null
  try {
    const result = await everMemosAPI.testConnection({
      api_base_url: cfg.value.api_base_url,
      timeout: Math.min(cfg.value.timeout, 5),
    })
    healthStatus.value = result.success
    if (result.success) {
      toast.success(t('settings.evermemos.testSuccess'))
    } else {
      toast.error(result.message || t('settings.evermemos.testFailed'))
    }
  } catch (e: any) {
    healthStatus.value = false
    toast.error(t('settings.evermemos.testFailed'))
  } finally {
    testing.value = false
  }
}

// ── 记忆预览 ───────────────────────────────────────────────────────────────
async function loadMemoryPreview() {
  previewLoading.value = true
  previewError.value = ''
  try {
    const result = await everMemosAPI.getMemories({ limit: 8 })
    if (result.success) {
      previewMemories.value = result.memories || []
    } else {
      previewError.value = result.message || t('settings.evermemos.previewFailed')
    }
  } catch (e: any) {
    previewError.value = e.message || t('settings.evermemos.previewFailed')
  } finally {
    previewLoading.value = false
  }
}

function getMemoryContent(mem: any): string {
  return (
    mem?.content ||
    mem?.summary ||
    mem?.episode ||
    mem?.subject ||
    mem?.title ||
    mem?.text ||
    JSON.stringify(mem).slice(0, 120)
  )
}

function getMemoryTime(mem: any): string {
  return (
    mem?.created_at ||
    mem?.timestamp ||
    mem?.start_time ||
    mem?.updated_at ||
    ''
  )
}

function formatMemoryTime(mem: any): string {
  const raw = getMemoryTime(mem)
  if (!raw) return '未知时间'
  const d = new Date(raw)
  if (Number.isNaN(d.getTime())) return String(raw)
  return d.toLocaleString()
}

const timelineMemories = computed(() => {
  return [...previewMemories.value].sort((a, b) => {
    const ta = new Date(getMemoryTime(a) || 0).getTime()
    const tb = new Date(getMemoryTime(b) || 0).getTime()
    return tb - ta
  })
})

function getMemoryTypeLabel(type: string): string {
  const key = `settings.evermemos.memoryTypes.${type}`
  const translated = t(key)
  // 若 key 不存在（t() 返回 key 本身），则直接返回原始值
  return translated === key ? type : translated
}
</script>

<style scoped>
.evermemos-config {
  padding: 0;
}

.section-header {
  margin-bottom: 24px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 6px;
}

.section-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0;
}

.form-group {
  margin-bottom: 20px;
}

.label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 6px;
}

.hint-text {
  font-size: 12px;
  color: var(--text-tertiary);
  margin: 4px 0 0;
}

.optional-tag {
  font-size: 11px;
  color: var(--text-tertiary);
  font-weight: 400;
  margin-left: 4px;
}

/* 开关行 */
.toggle-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.toggle-info {
  flex: 1;
}

.toggle-info .label {
  margin-bottom: 2px;
}

/* Toggle Switch */
.toggle-switch {
  position: relative;
  display: inline-block;
  width: 40px;
  height: 22px;
  flex-shrink: 0;
  margin-top: 2px;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  cursor: pointer;
  inset: 0;
  background: var(--border-color);
  border-radius: 22px;
  transition: 0.2s;
}

.toggle-slider::before {
  content: '';
  position: absolute;
  width: 16px;
  height: 16px;
  left: 3px;
  top: 3px;
  background: white;
  border-radius: 50%;
  transition: 0.2s;
}

.toggle-switch input:checked + .toggle-slider {
  background: var(--primary-color, #6366f1);
}

.toggle-switch input:checked + .toggle-slider::before {
  transform: translateX(18px);
}

.toggle-switch input:disabled + .toggle-slider {
  opacity: 0.5;
  cursor: not-allowed;
}

/* input with action button */
.input-with-action {
  display: flex;
  gap: 8px;
  align-items: stretch;
}

.input-with-action :deep(.input-wrapper),
.input-with-action :deep(input) {
  flex: 1;
}

/* 健康状态 */
.health-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  margin-top: 6px;
  font-weight: 500;
}

.health-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.health-status.healthy {
  color: var(--success-color, #10b981);
}

.health-status.healthy .health-dot {
  background: var(--success-color, #10b981);
}

.health-status.unhealthy {
  color: var(--error-color, #ef4444);
}

.health-status.unhealthy .health-dot {
  background: var(--error-color, #ef4444);
}

/* 数字输入 */
.number-input-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.number-input {
  width: 80px;
  padding: 6px 10px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  font-size: 13px;
  color: var(--text-primary);
  background: var(--bg-primary);
}

.number-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.unit-label {
  font-size: 13px;
  color: var(--text-secondary);
}

/* Select */
.select-input {
  width: 100%;
  padding: 7px 10px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  font-size: 13px;
  color: var(--text-primary);
  background: var(--bg-primary);
  cursor: pointer;
}

.select-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Disabled section */
.disabled-section {
  opacity: 0.55;
  pointer-events: none;
}

/* 记忆预览 */
.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.preview-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.view-mode-switch {
  display: flex;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  overflow: hidden;
}

.view-mode-btn {
  border: none;
  background: var(--bg-primary);
  color: var(--text-secondary);
  font-size: 12px;
  padding: 4px 10px;
  cursor: pointer;
}

.view-mode-btn.active {
  background: var(--primary-color, #6366f1);
  color: #fff;
}

.preview-header .label {
  margin-bottom: 0;
}

.memory-preview-box {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 12px;
  min-height: 80px;
  max-height: 240px;
  overflow-y: auto;
  background: var(--bg-primary);
}

.preview-loading,
.preview-empty,
.preview-error {
  font-size: 13px;
  color: var(--text-tertiary);
  text-align: center;
  padding: 16px 0;
}

.preview-error {
  color: var(--error-color, #ef4444);
}

.preview-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.preview-item {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 12px;
  line-height: 1.5;
}

.mem-main {
  flex: 1;
}

.mem-index {
  color: var(--text-tertiary);
  flex-shrink: 0;
  min-width: 18px;
}

.mem-content {
  flex: 1;
  color: var(--text-primary);
  word-break: break-word;
}

.mem-meta-row {
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.mem-time {
  color: var(--text-tertiary);
  font-size: 11px;
}

.mem-type-badge {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 10px;
  background: var(--primary-color-light, rgba(99,102,241,0.12));
  color: var(--primary-color, #6366f1);
  flex-shrink: 0;
  margin-top: 2px;
}

.mem-group {
  color: var(--text-tertiary);
  font-size: 11px;
}

.timeline-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.timeline-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.timeline-dot {
  width: 8px;
  height: 8px;
  margin-top: 6px;
  border-radius: 50%;
  background: var(--primary-color, #6366f1);
  flex-shrink: 0;
}

.timeline-content {
  flex: 1;
  border-left: 1px solid var(--border-color);
  padding-left: 10px;
}

.timeline-time {
  font-size: 11px;
  color: var(--text-tertiary);
  margin-bottom: 4px;
}

.timeline-text {
  font-size: 12px;
  color: var(--text-primary);
  line-height: 1.5;
  word-break: break-word;
}
</style>
