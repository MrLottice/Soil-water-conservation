<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  Promotion, 
  VideoPlay, 
  Warning, 
  Medal, 
  InfoFilled, 
  List, 
  DocumentCopy, 
  Download 
} from '@element-plus/icons-vue'

const paperInfo = ref('')
const submissionGenerated = ref(false)
const generatedSubmission = ref('')
const isLoading = ref(false)
const isCopying = ref(false)
const isDownloading = ref(false)
const rawContent = ref('')

const clearInputs = () => {
  paperInfo.value = ''
  generatedSubmission.value = ''
  rawContent.value = ''
}

const generateSubmission = async () => {
  if (!paperInfo.value.trim()) {
    ElMessage.error('请先输入方案标题')
    return
  }

  try {
    isLoading.value = true
    submissionGenerated.value = false
    generatedSubmission.value = ''
    rawContent.value = ''
    
    // 创建FormData对象
    const formData = new FormData()
    formData.append('name', paperInfo.value)
    
    console.log('发送请求的数据:', {
      url: '/api/shuibao_api',
      method: 'POST',
      formData: Object.fromEntries(formData.entries())
    })
    
    // 使用fetch API发送请求并处理流式响应
    const response = await fetch('/api/shuibao_api', {
      method: 'POST',
      body: formData
    })

    console.log('服务器响应状态:', response.status, response.statusText)
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    // 立即设置submissionGenerated为true，显示结果区域
    submissionGenerated.value = true

    // 创建响应流读取器
    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('无法获取响应流')
    }

    const decoder = new TextDecoder()
    let buffer = ''
    let isReading = true

    while (isReading) {
      const { done, value } = await reader.read()
      
      if (done) {
        isReading = false
        break
      }

      // 将接收到的数据添加到缓冲区
      buffer += decoder.decode(value, { stream: true })

      // 处理缓冲区中的完整消息
      const lines = buffer.split('\n\n')
      buffer = lines.pop() || '' // 保留最后一个不完整的消息

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            
            if (data.type === 'text') {
              // 直接使用full_text作为当前完整内容
              rawContent.value = data.full_text
              // 将完整的Markdown内容转换为HTML
              const htmlContent = markdownToHtml(rawContent.value)
              // 更新内容
              generatedSubmission.value = htmlContent
            } else if (data.type === 'done') {
              // 生成完成
              ElMessage.success('水土保持方案生成成功！')
              isReading = false
            } else if (data.type === 'error') {
              // 处理错误
              ElMessage.error(data.message || '生成过程中发生错误')
              isReading = false
            }
          } catch (e) {
            console.error('解析响应数据失败:', e)
          }
        }
      }
    }
  } catch (error: any) {
    console.error('API请求错误:', error)
    
    if (error.name === 'AbortError') {
      ElMessage.error('请求超时，服务器响应时间过长')
    } else if (error.response) {
      const status = error.response.status || '未知'
      const message = error.response.data?.message || '未知错误'
      ElMessage.error(`服务器错误 (${status}): ${message}`)
    } else {
      ElMessage.error('网络请求失败，请检查后端服务是否启动')
    }
  } finally {
    isLoading.value = false
  }
}

// 辅助函数：将Markdown文本转换为HTML
const markdownToHtml = (markdownText: string): string => {
  if (!markdownText || typeof markdownText !== 'string') {
    return markdownText || ''
  }
  
  if (markdownText.includes('<') && markdownText.includes('>')) {
    const markdownSpecificPatterns = [
      /^#{1,6}\s/m,       // 标题
      /\*\*(.*?)\*\*/,    // 加粗
      /\*([^*]+)\*/,     // 斜体
      /^[-*]\s/m,        // 无序列表
      /^\d+\.\s/m,       // 有序列表
      /\[(.*?)\]\((.*?)\)/, // 链接
      /!\[(.*?)\]\((.*?)\)/, // 图片
      /`([^`]+)`/,       // 行内代码
      /^```/,            // 代码块
      /^>/m,             // 引用
      /^---\s*$/m,       // 分割线
      /\|.*?\|/          // 表格
    ]
    const isLikelyMarkdown = markdownSpecificPatterns.some(pattern => pattern.test(markdownText))
    if (!isLikelyMarkdown) {
      return markdownText
    }
  }
  
  let processedText = markdownText
  
  // 处理代码块
  processedText = processedText.replace(/^```(\w*)\n([\s\S]*?)^```/gm, (match, lang, code) => {
    const languageClass = lang ? `language-${lang}` : ''
    const escapedCode = code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    return `<pre><code class="${languageClass}">${escapedCode.trim()}\n</code></pre>`
  })

  // 处理行内代码
  processedText = processedText.replace(/`([^`]+)`/g, '<code>$1</code>')

  // 处理标题
  processedText = processedText.replace(/^(#{1,6})\s+(.+)$/gm, (match, hashes, content) => {
    const level = hashes.length
    return `<h${level}>${content.trim()}</h${level}>`
  })

  // 处理加粗
  processedText = processedText.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  processedText = processedText.replace(/__([^_]+)__/g, '<strong>$1</strong>')
  
  // 处理斜体
  processedText = processedText.replace(/(^|[^*])\*([^*]+)\*($|[^*])/g, '$1<em>$2</em>$3')
  processedText = processedText.replace(/(^|[^_])_([^_]+)_($|[^_])/g, '$1<em>$2</em>$3')

  // 处理删除线
  processedText = processedText.replace(/~~(.*?)~~/g, '<del>$1</del>')

  // 处理链接
  processedText = processedText.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>')

  // 处理图片
  processedText = processedText.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1">')
  
  // 处理表格
  const tableRegex = /^\|.*?\|\r?\n\|.*?\|\r?\n(\|.*?\|\r?\n)*/gm
  processedText = processedText.replace(tableRegex, (tableMatch) => {
    const rows = tableMatch.trim().split(/\r?\n/)
    let tableHtml = '<table class="md-table">\n'
    
    const headerCells = rows[0].slice(1, -1).split('|').map(cell => `<th>${cell.trim()}</th>`).join('')
    tableHtml += `  <thead>\n    <tr>${headerCells}</tr>\n  </thead>\n`
    
    tableHtml += '  <tbody>\n'
    for (let i = 2; i < rows.length; i++) {
      const bodyCells = rows[i].slice(1, -1).split('|').map(cell => `<td>${cell.trim()}</td>`).join('')
      tableHtml += `    <tr>${bodyCells}</tr>\n`
    }
    tableHtml += '  </tbody>\n</table>'
    return tableHtml
  })

  // 处理块级引用
  processedText = processedText.replace(/^>\s+(.+)$/gm, '<blockquote>$1</blockquote>')

  // 处理分割线
  processedText = processedText.replace(/^(\*\*\*+|---|___)\s*$/gm, '<hr>')

  // 处理列表
  processedText = processedText.replace(/^[-*+]\s+(.+)$/gm, '<ul>\n<li>$1</li>\n</ul>')
  processedText = processedText.replace(/^\d+\.\s+(.+)$/gm, '<ol>\n<li>$1</li>\n</ol>')
  
  processedText = processedText.replace(/<\/ul>\n<ul>/g, '')
  processedText = processedText.replace(/<\/ol>\n<ol>/g, '')

  // 处理段落
  const lines = processedText.split(/\r?\n/)
  let inHtmlBlock = false
  const resultLines = lines.map(line => {
    const trimmedLine = line.trim()
    if (trimmedLine.startsWith('<') && trimmedLine.endsWith('>')) {
      if (trimmedLine.match(/^<(div|p|h[1-6]|ul|ol|li|table|thead|tbody|tr|th|td|blockquote|pre|hr)/i) || 
          trimmedLine.match(/^<\/(div|p|h[1-6]|ul|ol|li|table|thead|tbody|tr|th|td|blockquote|pre|hr)/i)) {
        if(trimmedLine.startsWith('<pre>')) inHtmlBlock = true
        if(trimmedLine.endsWith('</pre>')) inHtmlBlock = false
        return line
      }
    }
    if(inHtmlBlock && !trimmedLine.endsWith('</pre>')) return line
    if (trimmedLine === '') return ''
    return `<p>${line}</p>`
  })
  processedText = resultLines.filter(line => line !== '').join('\n')
  
  processedText = processedText.replace(/(<br\s*\/?>\s*){2,}/gi, '<br />')
  processedText = processedText.replace(/<p>\s*<br\s*\/?>\s*<\/p>/gi, '<br />')
  processedText = processedText.replace(/([^>])\n(?!<\/?(h[1-6]|ul|ol|li|p|div|pre|table|tr|td|th|blockquote|hr))/g, '$1<br />')

  return processedText
}

const copyContent = async () => {
  if (!generatedSubmission.value) {
    ElMessage.error('没有可复制的内容')
    return
  }
  
  try {
    isCopying.value = true
    const tempElement = document.createElement('div')
    tempElement.innerHTML = generatedSubmission.value
    const textContent = tempElement.textContent || tempElement.innerText || ''
    
    await navigator.clipboard.writeText(textContent)
    ElMessage.success('内容已复制到剪贴板')
  } catch (error) {
    console.error('复制失败:', error)
    ElMessage.error('复制失败，请手动复制')
  } finally {
    isCopying.value = false
  }
}

const downloadContent = () => {
  if (!generatedSubmission.value) {
    ElMessage.error('没有可下载的内容')
    return
  }
  
  try {
    isDownloading.value = true
    
    const wordContent = `
      <html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
      <head>
      <meta charset="utf-8">
      <title>${paperInfo.value || '水土保持方案'}</title>
      </head>
      <body>
      ${generatedSubmission.value}
      </body>
      </html>`
    
    let fileName = paperInfo.value.trim()
    if (fileName.length > 30) {
      fileName = fileName.substring(0, 30) + '...'
    }
    fileName = fileName.replace(/[\\/:*?"<>|]/g, '_')
    if (!fileName) {
      fileName = `水土保持方案_${new Date().toISOString().split('T')[0]}`
    }
    
    const blob = new Blob([wordContent], { type: 'application/vnd.ms-word;charset=utf-8' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `${fileName}.doc`
    link.click()
    
    URL.revokeObjectURL(link.href)
    ElMessage.success('水土保持方案已下载为Word文档')
  } catch (error) {
    console.error('下载失败:', error)
    ElMessage.error('下载失败，请稍后重试')
  } finally {
    setTimeout(() => {
      isDownloading.value = false
    }, 500)
  }
}
</script>

<template>
  <div class="journal-submission-container">
    <!-- 顶部标题栏 -->
    <div class="page-header">
      <div class="header-left">
        <el-icon class="light-bulb"><Promotion /></el-icon>
        <h2 class="page-title">水土保持方案生成</h2>
        <span class="version">v1.0.0</span>
      </div>
      <div class="header-right">
        <el-button class="tutorial-btn" type="primary" plain size="small">
          <el-icon><VideoPlay /></el-icon>
          <span>演示教程</span>
        </el-button>
      </div>
    </div>

    <!-- 主要内容区 -->
    <div class="main-content">
      <!-- 左侧输入区域 -->
      <div class="input-section">
        <div class="input-warning">
          <el-icon><Warning /></el-icon>
          <span>使用我们的服务时，确保您的输入和生成内容不违反任何适用法律和不侵犯第三方合法权益</span>
        </div>

        <!-- 方案标题输入 -->
        <div class="input-block">
          <div class="input-label">
            <el-icon class="label-icon blue"><Medal /></el-icon>
            <span class="label-text">方案标题<span class="required">*</span></span>
          </div>
          <el-input
            type="textarea"
            v-model="paperInfo"
            :rows="4"
            :maxlength="2000"
            placeholder="请输入方案的标题"
          />
          <div class="char-count">{{ paperInfo.length }} / 2000</div>
        </div>

        <!-- 操作按钮 -->
        <div class="action-buttons">
          <el-button size="large" plain @click="clearInputs" :disabled="isLoading">清空</el-button>
          <el-button size="large" type="primary" @click="generateSubmission" :loading="isLoading">
            {{ isLoading ? '生成中...' : '生成方案' }}
          </el-button>
        </div>

        <div class="disclaimer-text">
          内容由AI生成，注意甄别，仅供参考。
        </div>
      </div>

      <!-- 右侧结果区域 -->
      <div class="result-section">
        <div class="result-header">
          <el-icon class="result-icon"><List /></el-icon>
          <span class="result-title">生成结果</span>
        </div>

        <!-- 加载中状态 -->
        <div v-if="isLoading && !submissionGenerated" class="loading-result">
          <div class="loading-animation">
            <div class="loading-spinner"></div>
          </div>
          <p class="loading-text">AI正在生成水土保持方案...</p>
          <p class="loading-tips">这可能需要几分钟，请耐心等待</p>
        </div>

        <!-- 空结果状态 -->
        <div v-else-if="!isLoading && !submissionGenerated" class="empty-result">
          <div class="light-bulb-icon">
            <img src="https://img.icons8.com/ios/100/409eff/idea.png" alt="灵感" />
          </div>
          <p class="empty-text">暂无内容，尚未成功生成！</p>
        </div>

        <!-- 生成结果状态 -->
        <div v-else class="submission-result">
          <div class="submission-content" v-html="generatedSubmission"></div>
          <div class="result-actions">
            <el-button size="small" type="primary" plain @click="copyContent" :loading="isCopying">
              <el-icon><DocumentCopy /></el-icon>
              <span>复制</span>
            </el-button>
            <el-button size="small" type="success" plain @click="downloadContent" :loading="isDownloading">
              <el-icon><Download /></el-icon>
              <span>下载</span>
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.journal-submission-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  height: 100%;
  width: 100%;
  background-color: #f9f9f9;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 30px;
  background-color: #fff;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
  height: 64px;
}

.header-left {
  display: flex;
  align-items: center;
}

.light-bulb {
  color: #409EFF;
  font-size: 24px;
  margin-right: 10px;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #333;
}

.version {
  margin-left: 10px;
  color: #999;
  font-size: 14px;
}

.main-content {
  display: flex;
  flex: 1;
  padding: 20px;
  gap: 20px;
  overflow: hidden;
}

.input-section, .result-section {
  flex: 1;
  background-color: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  overflow-y: auto;
  max-height: calc(100vh - 104px);
}

.input-warning {
  display: flex;
  align-items: flex-start;
  padding: 10px 15px;
  background-color: #ecf5ff;
  border-radius: 6px;
  margin-bottom: 20px;
  color: #409EFF;
  font-size: 14px;
  line-height: 1.5;
}

.input-warning .el-icon {
  margin-right: 8px;
  margin-top: 2px;
  flex-shrink: 0;
  color: #409EFF;
}

.input-block {
  margin-bottom: 25px;
}

.input-label {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}

.label-icon {
  margin-right: 8px;
  font-size: 18px;
}

.blue {
  color: #409EFF;
}

.label-text {
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.required {
  color: #f56c6c;
  margin-left: 2px;
}

.char-count {
  text-align: right;
  color: #999;
  font-size: 12px;
  margin-top: 5px;
}

.action-buttons {
  display: flex;
  justify-content: center;
  gap: 15px;
  margin-top: 30px;
  margin-bottom: 20px;
}

.disclaimer-text {
  text-align: center;
  color: #999;
  font-size: 12px;
  margin-top: 20px;
}

.result-header {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid #eee;
}

.result-icon {
  color: #409EFF;
  font-size: 20px;
  margin-right: 8px;
}

.result-title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.empty-result {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: #999;
}

.light-bulb-icon {
  width: 80px;
  height: 80px;
  margin-bottom: 20px;
}

.light-bulb-icon img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.empty-text {
  font-size: 16px;
  color: #999;
}

.submission-result {
  padding: 10px;
}

.submission-content {
  margin-bottom: 20px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
  overflow-wrap: break-word;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

.submission-content :deep(h1),
.submission-content :deep(h2),
.submission-content :deep(h3),
.submission-content :deep(h4),
.submission-content :deep(h5),
.submission-content :deep(h6) {
  margin-top: 1em;
  margin-bottom: 0.5em;
  line-height: 1.4;
}

.submission-content :deep(p) {
  margin-bottom: 1em;
}

.submission-content :deep(ul),
.submission-content :deep(ol) {
  margin: 1em 0;
  padding-left: 2em;
}

.submission-content :deep(li) {
  margin: 0.5em 0;
}

.submission-content :deep(code) {
  background-color: #f5f7fa;
  padding: 0.2em 0.4em;
  border-radius: 3px;
  font-family: Consolas, Monaco, 'Andale Mono', monospace;
}

.submission-content :deep(pre) {
  background-color: #f5f7fa;
  padding: 1em;
  border-radius: 4px;
  overflow-x: auto;
  margin: 1em 0;
}

.submission-content :deep(blockquote) {
  border-left: 4px solid #409EFF;
  margin: 1em 0;
  padding: 0.5em 1em;
  background-color: #f5f7fa;
}

.submission-content :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 1em 0;
}

.submission-content :deep(th),
.submission-content :deep(td) {
  border: 1px solid #dcdfe6;
  padding: 0.5em;
  text-align: left;
}

.submission-content :deep(th) {
  background-color: #f5f7fa;
}

.result-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}

.loading-result {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 400px;
  color: #409EFF;
}

.loading-animation {
  position: relative;
  width: 80px;
  height: 80px;
  margin-bottom: 30px;
}

.loading-spinner {
  position: absolute;
  top: 0;
  left: 0;
  width: 80px;
  height: 80px;
  border: 5px solid rgba(64, 158, 255, 0.2);
  border-top-color: #409EFF;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.loading-spinner::after {
  content: "";
  position: absolute;
  top: 15px;
  left: 15px;
  right: 15px;
  bottom: 15px;
  border: 3px solid rgba(64, 158, 255, 0.2);
  border-top-color: #409EFF;
  border-radius: 50%;
  animation: spin 1.5s linear infinite reverse;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

.loading-text {
  font-size: 18px;
  font-weight: 500;
  color: #409EFF;
  margin-bottom: 10px;
}

.loading-tips {
  font-size: 14px;
  color: #909399;
  text-align: center;
  max-width: 300px;
  line-height: 1.5;
}
</style>
