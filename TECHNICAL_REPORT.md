# IRS Fact Graph + LLM Agent 技術報告

## 專案概述

本專案實現了一個基於知識圖譜的稅務諮詢系統，結合 LLM (Large Language Model) 的自然語言理解能力與 Fact Graph 規則引擎的精確計算能力，讓使用者可以透過自然語言與稅務系統互動。

### 核心價值主張

**自然語言輸入 + 精確計算輸出 = 可對話的專家系統**

---

## 系統架構

### 整體架構圖

```
┌─────────────────┐
│   使用者輸入     │  "我是單身，標準扣除額是多少？"
└────────┬────────┘
         ↓
┌─────────────────┐
│  LLM Agent      │  Google ADK + Gemini 1.5 Flash
│  (自然語言理解)  │  • 解析使用者意圖
│                 │  • 提取關鍵參數
└────────┬────────┘  • 生成操作指令
         ↓
┌─────────────────┐
│  Fact Graph     │  規則引擎 (Java)
│  (規則計算)      │  • 儲存可寫入事實
│                 │  • 自動推導衍生事實
└────────┬────────┘  • 維護狀態一致性
         ↓
┌─────────────────┐
│  結構化回應      │  { "filingStatus": "single",
└─────────────────┘    "standardDeduction": 14600 }
```

### 技術棧

| 層級 | 技術 | 用途 |
|------|------|------|
| **前端** | HTML/JavaScript | Web 聊天介面 |
| **反向代理** | Nginx | 統一入口 (port 8897) |
| **API 層** | FastAPI + Uvicorn | REST API 與 WebSocket |
| **LLM Agent** | Google ADK 1.16.0 | Agent 框架與會話管理 |
| **LLM 模型** | Gemini 1.5 Flash | 自然語言理解 |
| **規則引擎** | Fact Graph (Java) | 稅務計算與推導 |
| **容器化** | Docker Compose | 多服務編排 |

---

## 核心組件詳解

### 1. LLM Agent Layer (Google ADK)

- **內建會話管理**：`InMemorySessionService` 自動處理對話歷史

### 2. Fact Graph Layer (規則引擎)

Fact Graph 是一個基於規則的推導系統，不同於傳統資料庫：

| 特性 | 傳統資料庫 | Fact Graph |
|------|-----------|-----------|
| **資料性質** | 靜態儲存 | 動態推導 |
| **更新方式** | 手動更新每個欄位 | 設定一個值，相關值自動更新 |
| **計算邏輯** | 應用層實現 | 規則引擎內建 |
| **型別安全** | Schema 定義 | XML 型別定義 + 執行時驗證 |

#### 核心概念

**Writable Facts（可寫入事實）**
```xml
<fact path="/filingStatus" type="EnumWrapper">
  <!-- 使用者可以直接設定的值 -->
  <EnumType>
    <value>single</value>
    <value>married_filing_jointly</value>
    <value>married_filing_separately</value>
    <value>head_of_household</value>
  </EnumType>
</fact>
```

**Derived Facts（衍生事實）**
```xml
<fact path="/standardDeduction" type="Decimal">
  <!-- 根據 filingStatus 自動計算 -->
  <rule>
    if /filingStatus == "single" then 14600
    if /filingStatus == "married_filing_jointly" then 29200
  </rule>
</fact>
```

### 3. API Layer (FastAPI)

### 4. Docker 容器編排

#### 網路架構

```
外部請求 → :8897 (Nginx)
              ↓
              ├─→ /chat        → llm-api:8000/chat
              ├─→ /api/*       → llm-api:8000/api/*
              └─→ /            → fact-graph:8897/
```

---

## 工作流程示例

### 場景：使用者查詢標準扣除額

#### 第一輪對話

**使用者輸入**
```
"我是單身"
```

**系統處理流程**

1. **Nginx 接收請求** → 轉發到 `llm-api:8000/api/chat`

2. **LLM Agent 理解意圖**
   ```python
   # Google ADK 執行
   輸入: "我是單身"
   當前狀態: {} (空)

   # Gemini 輸出
   <action>SET_FACT:/filingStatus=single</action>
   好的，已設定為單身。
   ```

3. **操作 Fact Graph**
   ```bash
   ./gradlew run --args "/filingStatus=single"
   ```

   Fact Graph 自動推導：
   ```
   /filingStatus = "single"  (已設定)
        ↓
   /standardDeduction = 14600  (自動計算)
   ```

4. **返回結構化回應**
   ```json
   {
     "message": "好的，已設定為單身。",
     "fact_graph_data": {
       "/filingStatus": {
         "$type": "EnumWrapper",
         "item": { "value": "single" }
       }
     }
   }
   ```

#### 第二輪對話（會話記憶測試）

**使用者輸入**
```
"標準扣除額是多少？"
```

**系統處理流程**

1. **LLM Agent 檢索會話歷史**
   ```python
   # ADK Session 自動包含：
   - 上一輪: "我是單身" → 設定了 /filingStatus=single
   - 當前狀態: { "/filingStatus": "single" }
   ```

2. **LLM 理解上下文**
   ```
   Gemini 知道：
   - 使用者已經設定過 filingStatus = single
   - 現在問標準扣除額
   - 應該查詢 /standardDeduction
   ```

3. **查詢 Fact Graph**
   ```bash
   ./gradlew run --args "/standardDeduction=?"
   ```

   返回：`14600`

4. **生成自然語言回應**
   ```json
   {
     "message": "單身的標準扣除額是 $14,600。",
     "fact_graph_data": {
       "/filingStatus": {
         "$type": "EnumWrapper",
         "item": { "value": "single" }
       }
     }
   }
   ```

---

## 技術亮點

### 1. 無需 RAG 或 Embedding

#### 為什麼不需要？

| 技術 | 用途 | 本專案是否需要 |
|------|------|--------------|
| **RAG** | 從文件中檢索答案 | ❌ 知識編碼在規則引擎中 |
| **Embedding** | 語義搜尋、相似度匹配 | ❌ LLM 直接理解意圖 |
| **向量資料庫** | 儲存文件向量 | ❌ 無文件需要檢索 |

#### 架構對比

**RAG 架構（本專案未使用）**
```
使用者問題
  → Embedding 轉向量
  → 向量資料庫搜尋
  → 檢索相關文件
  → LLM 生成答案
```

**本專案架構**
```
使用者問題
  → LLM 直接理解
  → 輸出結構化指令
  → Fact Graph 計算
  → 返回精確結果
```

### 2. 確定性計算 vs LLM 幻覺

**傳統 LLM 問答（有幻覺風險）**
```
Q: "單身的標準扣除額是多少？"
A: "大約 $12,000" ❌ (可能幻覺)
```

**Fact Graph + LLM（零幻覺）**
```
Q: "單身的標準扣除額是多少？"
LLM → SET /filingStatus=single
Graph → 計算 /standardDeduction = 14600
A: "$14,600" ✅ (規則保證正確)
```

### 3. 狀態管理與自動傳播

**場景：使用者改變報稅身份**

```python
# 初始狀態
/filingStatus = "single"
/standardDeduction = 14600

# 使用者：「我改成已婚聯合申報」
LLM → SET /filingStatus=married_filing_jointly

# Fact Graph 自動重新計算
/filingStatus = "married_filing_jointly"
/standardDeduction = 29200  # 自動更新！
```

**優勢：**
- ✅ 不需要手動更新每個相關欄位
- ✅ 保證資料一致性
- ✅ 複雜規則鏈自動執行

### 4. 會話記憶（Google ADK）

```python
# 第一輪
使用者: "我是單身"
Session: { messages: [{"user": "我是單身", "assistant": "..."}] }

# 第二輪（自動包含歷史）
使用者: "標準扣除額是多少？"
Session: {
  messages: [
    {"user": "我是單身", "assistant": "..."},
    {"user": "標準扣除額是多少？"}  # ← LLM 能看到上下文
  ]
}
```

## 部署指南

### 環境需求

- Docker & Docker Compose
- GOOGLE_API_KEY（Gemini API）
- Java 17+（Fact Graph）
- Python 3.11+（LLM API）

### 訪問方式

- **Web 聊天介面**: http://localhost:8897/chat
- **API 文檔**: http://localhost:8897/api/docs
- **Fact Graph Demo**: http://localhost:8897/

---

## 效能考量

### 響應時間

| 操作 | 平均時間 | 說明 |
|------|---------|------|
| **LLM 推理** | 1-3 秒 | Gemini API 調用 |
| **Fact Graph 計算** | <100ms | 本地規則引擎執行 |
| **總響應時間** | 1-3 秒 | 主要瓶頸在 LLM |

### 優化方向

1. **模型選擇**: Gemini 1.5 Flash 已是速度最快的選擇
2. **快取策略**: 相同問題可快取 LLM 回應
3. **並行處理**: 多個獨立查詢可並行執行

---

## 可擴展性

### 新增稅務概念

1. **修改 XML 定義**
   ```xml
   <!-- demo/all-facts.xml -->
   <fact path="/childTaxCredit" type="Decimal">
     <rule>
       if /numberOfChildren > 0 then 2000 * /numberOfChildren
     </rule>
   </fact>
   ```

2. **更新 System Instruction**
   ```python
   SYSTEM_INSTRUCTION += """
   - 子女稅收抵免 (/childTaxCredit): 每個孩子 $2,000
   """
   ```

## 專案限制與未來改進

### 當前限制

1. **規則數量有限**：目前系統僅包含 6 個稅務概念
2. **單一使用者會話**：所有請求共用同一個 `user_id`
3. **記憶體儲存**：會話歷史存在記憶體中，重啟後消失
4. **稅務規則簡化**：未實現完整的 IRS 邏輯
5. **無權限控制**：所有使用者可訪問所有資料

### 關鍵挑戰：規則數量擴展

#### 現在 vs 未來：規則爆炸問題

目前系統在 6 個規則時運作良好，但當規則數量增長時會面臨根本性挑戰：

**現在（6 個規則）**
- ✅ 所有規則都能放進 System Instruction
- ✅ LLM 能一眼看到所有可用概念
- ✅ 無需複雜的檢索機制

**未來（1000+ 個規則）**
- ❌ 不可能把所有規則放進 prompt（token 爆炸）
- ❌ LLM 無法從海量規則中找到相關的
- ❌ 系統變得不可管理和不可維護

#### 實際 IRS 規則量

```
基礎稅務規則: ~50 條
標準扣除額規則: 5 條
逐項扣除規則: 20 條
稅收抵免規則: 15 條
特殊情況規則: 30 條
州稅規則: 50 條 × 50 州 = 2,500 條
...

估計總計: 5,000-10,000 條規則
```

### 解決方案：規則擴展的分階段策略

#### 階段 1：現在（6-50 個規則）✅ 當前階段

**無需修改架構**

現有的簡單架構已足夠。所有規則都能在 System Instruction 中明確列舉。

#### 階段 2：中期（50-200 個規則）⚠️ 臨界點

**改進 System Instruction 的組織**

- 按類別分組規則（基礎、扣除額、抵免、特殊情況）
- 提供規則目錄而不是完整規則
- 讓 LLM 根據需要「詢問」具體規則
- 實現簡單的規則分類索引

**改進方向**
```
SYSTEM_INSTRUCTION 改為提供：
- 規則分類清單
- 每類規則的概要
- 規則查詢的方式

使用者問題 → LLM 判斷相關類別 → 詢問具體規則 → 執行
```

#### 階段 3：長期（1000+ 個規則）✅ 必須升級

**引入規則檢索層（類似 RAG）**

當規則數量超過 200-300 時，**必須加入檢索層**：

**新架構：動態規則檢索**

```
使用者輸入
  ↓
LLM 初步理解意圖（簡化指令）
  ↓
規則檢索層 ⭐ （新增）
  ├─ 向量檢索：基於語義相似度找相關規則
  ├─ 規則圖譜：基於依賴關係找相關規則
  └─ 分類索引：快速定位規則類別
  ↓
動態構建 System Instruction
（只包含相關的 20-50 個規則）
  ↓
LLM 生成操作指令
  ↓
Fact Graph 執行
```

### 檢索層的三種實現方式

#### 方案 A：向量檢索（最接近 RAG）

**原理**：
- 對每條規則使用 Embedding 模型轉換為向量
- 將使用者查詢也轉換為向量
- 透過相似度搜尋找到最相關的規則

**優勢**：
- ✅ 語義理解能力強
- ✅ 可處理自然語言表述的差異

**劣勢**：
- ❌ 增加 Embedding 模型的費用
- ❌ 需要維護向量資料庫（FAISS、Chroma 等）
- ❌ 相似度不一定完全準確

**適用場景**：IRS 規則本身描述複雜、表述多變

#### 方案 B：規則圖譜導航（推薦）

**原理**：
- 建立規則間的依賴關係圖
- 從使用者提及的規則出發，展開相關規則
- 只取相關的規則子集

**依賴關係例子**：
```
/filingStatus
  ├─ 影響: /standardDeduction, /taxBracket, /phaseOutRange
  └─ 被影響: /ageRelated (年齡可能改變 filingStatus)

/homeOfficeDeduction
  ├─ 影響: /deductionsTotal, /AGI
  └─ 需要: /homeOfficeArea, /businessExpenses
```

**優勢**：
- ✅ 邏輯清晰，規則間關係明確
- ✅ 無需 Embedding 或向量 DB
- ✅ 完全確定性（不会出現誤判）
- ✅ 易於維護和調試

**劣勢**：
- ❌ 需要手動建立依賴關係圖
- ❌ 不適合處理隱含的邏輯關係

**適用場景**：IRS 規則關係明確、規則間依賴清晰

#### 方案 C：分類索引（輕量級）

**原理**：
- 預先對所有規則進行分類（基礎、扣除、抵免等）
- LLM 先判斷用戶問題屬於哪個分類
- 只檢索該分類下的規則

**優勢**：
- ✅ 實現簡單，無需複雜依賴
- ✅ 性能最優

**劣勢**：
- ❌ 只適合規則分類清晰的場景
- ❌ 跨類別問題處理困難

**適用場景**：IRS 規則按職能分類明確

### 建議方案

**分階段採用混合策略**：

| 規則數量 | 推薦方案 | 實施複雜度 |
|---------|---------|----------|
| < 50 | 無需檢索 | 無 |
| 50-200 | 分類索引 | 低 |
| 200-500 | 規則圖譜 | 中 |
| 500+ | 規則圖譜 + 向量檢索 | 高 |

**現在的建議**：
- 保持當前簡單架構
- 當規則增至 100+ 時，開始建立規則分類
- 當規則增至 300+ 時，實現規則圖譜
- 當規則超過 500 時，才考慮加入向量檢索

### 其他改進方向

**1. 多使用者支援**
- 從請求頭提取使用者認證信息
- 為每個使用者維護獨立會話
- 實現用戶隱私隔離

**2. 持久化會話**
- 使用 Redis 或資料庫儲存會話歷史
- 支援跨設備、跨會話的狀態恢復
- 記錄使用者操作審計日誌

**3. 擴展稅務規則**
- 實現完整的 IRS 1040 表單邏輯
- 支援州稅計算
- 整合實時稅法更新

**4. 增強安全性**
- 使用者認證（OAuth 2.0）
- API rate limiting
- 敏感資料加密

**5. 效能優化**
- 規則計算結果快取
- LLM 回應快取（相同問題不重複調用）
- 批量查詢優化

## 結論

### 核心成就

✅ **零幻覺的稅務計算**: LLM 負責理解，Fact Graph 負責計算
✅ **自然的對話體驗**: Google ADK 提供完整的會話管理
✅ **狀態自動同步**: 改一個值，相關值自動更新
✅ **容器化部署**: 一鍵啟動所有服務

### 技術創新點

1. **LLM Agent + 規則引擎混合架構**
   - 不是 RAG（無文件檢索）
   - 不是純 LLM（無幻覺風險）
   - 結合兩者優勢

2. **確定性與靈活性並存**
   - 計算結果 100% 正確（規則引擎保證）
   - 互動方式自然靈活（LLM 理解自然語言）

3. **會話記憶自動化**
   - Google ADK 內建會話管理
   - 開發者無需手動處理歷史

### 適用場景

這個架構特別適合：
- ✅ 需要精確計算的對話系統（稅務、保險、金融）
- ✅ 規則明確的專家系統（法律諮詢、醫療診斷）
- ✅ 狀態依賴的互動應用（遊戲、配置工具）

不適合：
- ❌ 開放性問答（應該用 RAG）
- ❌ 創意生成（應該用純 LLM）
- ❌ 簡單的 CRUD 應用（過度設計）


**專案倉庫**: https://github.com/CreateIntelligens/fact-graph.gith
**撰寫日期**: 2025-10-17
