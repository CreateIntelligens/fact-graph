import * as fg from './fg.js'

let factGraph

function loadDictionary(event) {
  const file = event.target.files[0]
  const reader = new FileReader()
  reader.onload = () => setGraph(reader.result)
  reader.readAsText(file)
}

function setGraph(text) {
  const factDictionary = fg.FactDictionaryFactory.importFromXml(text)
  factGraph = fg.GraphFactory.apply(factDictionary)

  const options = factGraph.paths().map(path => {
    return `<option value="${path}">${path}</option>`
  })
  document.querySelector('#facts').innerHTML = options

  setError()
  displayGraph()
  resetCollectionResult()
}

function getFact(event) {
  event.preventDefault()
  const form = event.target
  const path = form['get-fact'].value

  if (!factGraph) {
    setError('請先載入 Fact Dictionary 後再查詢。')
    return
  }

  if (path.includes('/*')) {
    setError('路徑仍包含 *，請使用實際的 UUID 後再查詢。')
    return
  }

  const uuidMatch = path.match(/#([0-9a-fA-F-]+)/)
  if (uuidMatch && uuidMatch[1].length !== 36) {
    setError('UUID 格式不正確，正確格式應為 36 個字元（包含連字號）。')
    return
  }

  try {
    const result = factGraph.getFact(path)
    document.querySelector('#fact-result').innerText = stringifyResult(result)
    setError()
  } catch (e) {
    setError(formatError(e))
    document.querySelector('#fact-result').innerText = ''
  }
}

function setFact(event) {
  event.preventDefault()
  const form = event.target
  const path = form['fact'].value
  const value = form['value'].value

  if (!factGraph) {
    setError('請先載入 Fact Dictionary 後再儲存資料。')
    return
  }

  if (path.includes('/*')) {
    setError('路徑仍包含 *，請使用實際的 UUID（例如 /formW2s/#123e4567-e89b-12d3-a456-426614174000/欄位）。')
    return
  }

  const uuidMatch = path.match(/#([0-9a-fA-F-]+)/)
  if (uuidMatch && uuidMatch[1].length !== 36) {
    setError('UUID 格式不正確，正確格式應為 36 個字元（包含連字號）。')
    return
  }

  try {
    const saveResult = factGraph.set(path, value)
    handleLimitViolations(saveResult)
  } catch (e) {
    setError(formatError(e))
    return
  }

  displayGraph()
}

function listCollectionPaths(event) {
  event.preventDefault()
  const form = event.target
  const basePath = form['collection'].value.trim()

  if (!factGraph) {
    setError('請先載入 Fact Dictionary 後再查詢集合定義。')
    return
  }

  if (!basePath) {
    setError('請輸入集合路徑，例如 /formW2s')
    resetCollectionResult()
    return
  }

  try {
    const normalized = basePath.endsWith('/*') ? basePath : `${basePath}/*`
    const availablePaths = factGraph
      .paths()
      .filter(path => path.startsWith(normalized.replace('*', '')))
    if (availablePaths.length === 0) {
      document.querySelector('#collection-result').innerText =
        '找不到對應的集合路徑定義。請確認輸入是否正確。'
    } else {
      const explanation = [
        `集合 '${basePath}' 的定義路徑：`,
        ...availablePaths.map(path => `• ${path}`),
        '',
        '請將其中的 * 替換成實際的 UUID，例如 /formW2s/#123e4567-e89b-12d3-a456-426614174000/欄位名稱。',
      ].join('\n')
      document.querySelector('#collection-result').innerText = explanation
    }
    setError()
  } catch (e) {
    setError(formatError(e))
    resetCollectionResult()
  }
}

function displayGraph() {
  if (!factGraph) return
  const json = factGraph.toJSON()
  const prettyJson = JSON.stringify(JSON.parse(json), null, 2) // I know
  document.querySelector('#graph').innerText = prettyJson
}

function setError(msg) {
  const errorDiv = document.querySelector('#error')
  if (!msg) {
    errorDiv.classList.add('hidden')
  } else {
    errorDiv.classList.remove('hidden')
    errorDiv.innerText = sanitizeMessage(msg)
  }
}

function resetCollectionResult() {
  document.querySelector('#collection-result').innerText = ''
}

function handleLimitViolations(result) {
  if (!result || typeof result !== 'object') {
    setError()
    return
  }

  const violations = Array.isArray(result.limitViolations)
    ? result.limitViolations
    : JSON.parse(JSON.stringify(result.limitViolations ?? []))
  let valid = result.valid
  if (typeof valid !== 'boolean') {
    try {
      const serialized = JSON.parse(JSON.stringify(result))
      valid = serialized.valid
    } catch {
      valid = true
    }
  }

  if (valid === false) {
    const violationMessages = violations.map(formatViolation).join('\n')
    setError(violationMessages || '儲存失敗（未知限制違規）。')
    return
  }

  if (violations.length > 0) {
    const violationMessages = violations.map(formatViolation).join('\n')
    setError(violationMessages)
  } else {
    setError()
  }
}

function formatViolation(v) {
  const parts = [
    v.limitName ? `限制：${v.limitName}` : '',
    v.factPath ? `路徑：${v.factPath}` : '',
    v.limit ? `限制值：${v.limit}` : '',
    v.actual ? `實際值：${v.actual}` : '',
    v.level ? `等級：${v.level}` : '',
  ].filter(Boolean)

  return parts.join(' / ')
}

function formatError(error) {
  if (!error) return '發生未知錯誤。'
  if (typeof error === 'string') return error
  if (error.message) return error.message
  if (typeof error.toString === 'function') return error.toString()
  try {
    return JSON.stringify(error)
  } catch {
    return '發生錯誤，但無法取得詳細資訊。'
  }
}

function sanitizeMessage(msg) {
  if (typeof msg !== 'string') return String(msg ?? '')
  return msg.replace(/[^\x20-\x7E\u4E00-\u9FFF\u3040-\u30FF\uAC00-\uD7AF\uFF01-\uFF60\n\r\t]/g, '')
}

function stringifyResult(result) {
  // 處理 null, undefined
  if (result === null || result === undefined) {
    return String(result)
  }

  // 處理原始型別
  if (
    typeof result === 'string' ||
    typeof result === 'number' ||
    typeof result === 'boolean'
  ) {
    return String(result)
  }

  // 嘗試取得 Scala.js 物件的值
  if (result && typeof result === 'object') {
    // 如果有 item 屬性 (包裝型別)
    if ('item' in result) {
      return stringifyResult(result.item)
    }

    // 如果有 value 屬性
    if ('value' in result) {
      return stringifyResult(result.value)
    }

    // 如果有 toString 方法且不是預設的 [object Object]
    if (typeof result.toString === 'function') {
      const str = result.toString()
      // 避免顯示 Scala 物件的預設 toString (如 gov.irs.factgraph.Fact@19)
      if (!str.includes('@') && !str.startsWith('[object')) {
        return str
      }
    }
  }

  // 嘗試 JSON 序列化
  try {
    const serialized = JSON.stringify(result, getCircularReplacer(), 2)
    // 如果序列化結果有意義,返回它
    if (serialized && serialized !== '{}' && serialized !== '[]') {
      return serialized
    }
  } catch (e) {
    console.error('JSON stringify failed:', e)
  }

  // 最後嘗試直接轉換
  try {
    // 嘗試序列化整個物件來提取資訊
    const keys = Object.keys(result)
    if (keys.length > 0) {
      const info = keys.map(key => `${key}: ${result[key]}`).join('\n')
      return info
    }
  } catch (e) {
    console.error('Object inspection failed:', e)
  }

  return '無法顯示結果 (可能是未完成的 Fact 或需要先設定相關資料)'
}

function getCircularReplacer() {
  const seen = new WeakSet()
  return (key, value) => {
    if (typeof value === 'object' && value !== null) {
      if (seen.has(value)) {
        return '[Circular]'
      }
      seen.add(value)
    }
    return value
  }
}

window.loadDictionary = loadDictionary
window.setFact = setFact
window.getFact = getFact
window.listCollectionPaths = listCollectionPaths
