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