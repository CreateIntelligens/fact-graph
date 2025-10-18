"""
LLM 代理層
負責理解使用者意圖並轉換為 Fact Graph 操作
使用 Google ADK (Agent Development Kit) - 內建對話記錄功能
"""

import os
from typing import Dict, Optional
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService, Session
from google.adk.agents import Agent
from google.genai import types
from dotenv import load_dotenv

load_dotenv()


# 系統提示詞
SYSTEM_INSTRUCTION = """你是美國稅務助理，基於 IRS Fact Graph 回答問題。

## 回應原則
1. **簡潔直接**: 用 1-2 句話回答，不要冗長解釋
2. **智能判斷**: 如果使用者說「單身」就直接設定 /filingStatus=single，不要再問一次確認
3. **主動執行**: 能查的就直接查，不要問使用者要不要查
4. **記住資訊**: 使用者已經說過的資訊，不要重複詢問
5. **友善但專業**: 用口語化但專業的語氣

## 可用稅務概念

### 1. 報稅身份 (/filingStatus) - 可設定
- single: 單身
- married_filing_jointly: 已婚聯合申報
- married_filing_separately: 已婚分開申報
- head_of_household: 戶長
- qualifying_surviving_spouse: 符合資格的未亡人

### 2. 標準扣除額 (/standardDeduction) - 自動計算
- 需要先設定報稅身份
- 2024年金額：
  - 單身/已婚分開: $14,600
  - 已婚聯合/符合資格未亡人: $29,200
  - 戶長: $21,900

### 3. 預付保費稅額抵免 (/writableHasAdvancedPtc) - 可設定
- true: 有預付保費稅額抵免 (Advanced Premium Tax Credit)
- false: 沒有預付保費稅額抵免
- 說明：如果使用者透過 Healthcare.gov 購買保險並提前領取補助，需設定為 true

### 4. 預付稅額抵免狀態 (/hasAdvancedPtc) - 自動計算
- 根據 /writableHasAdvancedPtc 自動決定
- 這是推導值，不可直接設定

### 5. ACH 直接存款退稅 (/refundViaAch) - 可設定
- true: 透過 ACH 直接存款接收退稅
- false: 以郵寄支票方式接收退稅
- 說明：直接存款更快速，通常 21 天內到帳

### 6. ACH 付款 (/payViaAch) - 可設定
- true: 透過 ACH 進行即時電子付款
- false: 需稍後以其他方式付款（支票、匯款等）
- 說明：僅在需要補稅時才相關

## 操作格式
需要操作時使用:
<action>SET_FACT:/filingStatus=single</action>
<action>GET_FACT:/standardDeduction</action>

## 範例
使用者: 單身的標準扣除額是多少?
助理: <action>SET_FACT:/filingStatus=single</action><action>GET_FACT:/standardDeduction</action>
單身的標準扣除額是 $13,850。

**重要**: 只在必要時詢問，不要重複確認使用者已經說過的資訊。"""


class TaxAssistant:
    """稅務助理 - 使用 Google ADK"""

    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("請設定 GOOGLE_API_KEY 環境變數")

        # 建立會話服務 (ADK 內建對話記錄管理)
        self.session_service = InMemorySessionService()

        # 建立 Agent
        self.agent = Agent(
            name="tax_assistant",
            model="gemini-2.0-flash",
            description="美國稅務助理，提供 IRS Fact Graph 查詢功能",
            instruction=SYSTEM_INSTRUCTION,
            tools=[]  # 不使用 ADK 工具，手動處理 action
        )

        # 建立 Runner
        self.runner = Runner(
            app_name="fact_graph_tax_app",
            agent=self.agent,
            session_service=self.session_service
        )

        # 會話快取
        self.active_sessions = {}

        # 記住使用者已提供的資訊
        self.user_context = {}

        print("✅ Tax Assistant (Google ADK) 初始化完成")

    async def _get_or_create_session(self, user_id: str) -> Session:
        """獲取或建立用戶會話 (ADK 自動管理對話歷史)"""
        if user_id not in self.active_sessions:
            session_id = f"session_{user_id}"
            session = await self.session_service.create_session(
                app_name="fact_graph_tax_app",
                user_id=user_id,
                session_id=session_id
            )
            self.active_sessions[user_id] = session
            print(f"建立新會話: User={user_id}, Session={session_id}")
        else:
            session = self.active_sessions[user_id]
            print(f"使用現有會話: User={user_id}")

        return session

    async def chat(self, user_message: str, fact_graph_client) -> str:
        """
        處理使用者訊息

        Args:
            user_message: 使用者輸入
            fact_graph_client: Fact Graph 客戶端

        Returns:
            助理回應
        """
        # 使用固定的 user_id (單一用戶場景)
        user_id = "fact_graph_user"

        # 取得當前 Fact Graph 狀態
        current_facts = self._get_current_facts_summary(fact_graph_client)

        # 組合訊息 (包含當前狀態)
        full_message = f"""當前已知資訊:
{current_facts}

---

{user_message}"""

        # 獲取會話
        session = await self._get_or_create_session(user_id)

        # 轉換為 ADK Content 格式
        content = types.Content(
            role="user",
            parts=[types.Part(text=full_message)]
        )

        # 使用 Runner 執行 Agent (ADK 自動管理對話歷史)
        final_response = ""
        try:
            async for event in self.runner.run_async(
                user_id=user_id,
                session_id=session.id,
                new_message=content
            ):
                # 收集最終回應
                if hasattr(event, 'is_final_response') and event.is_final_response():
                    if hasattr(event, 'content') and event.content:
                        event_content = event.content
                        if hasattr(event_content, 'parts') and event_content.parts:
                            for part in event_content.parts:
                                if hasattr(part, 'text'):
                                    final_response += part.text
        except Exception as e:
            print(f"[LLM Error] {e}")
            import traceback
            traceback.print_exc()
            return "抱歉，我遇到了一些問題，請稍後再試。"

        # 解析並執行動作
        if final_response:
            final_response = self._execute_actions(final_response, fact_graph_client)
        else:
            final_response = "抱歉，我沒有產生回應。"

        return final_response

    def _get_current_facts_summary(self, fact_graph_client) -> str:
        """取得當前 Fact Graph 狀態摘要"""
        current_graph = fact_graph_client.get_current_graph()

        if not current_graph or len(current_graph) == 0:
            return "尚無資料"

        summary = []
        for path, value in current_graph.items():
            if isinstance(value, dict) and "$type" in value:
                if "item" in value:
                    actual_value = value["item"]
                    if isinstance(actual_value, dict) and "value" in actual_value:
                        summary.append(f"{path}: {actual_value['value']}")
                    else:
                        summary.append(f"{path}: {actual_value}")
                else:
                    summary.append(f"{path}: {value}")
            else:
                summary.append(f"{path}: {value}")

        return "\n".join(summary) if summary else "尚無資料"

    def _execute_actions(self, message: str, fact_graph_client) -> str:
        """解析並執行 LLM 產生的動作"""
        import re

        # 解析 SET_FACT 動作
        set_pattern = r'<action>SET_FACT:([^=]+)=([^<]+)</action>'
        for match in re.finditer(set_pattern, message):
            path = match.group(1).strip()
            value = match.group(2).strip()

            print(f"[Debug] SET_FACT: {path} = {value}")

            try:
                result = fact_graph_client.set_fact(path, value)
                self.user_context[path] = value
                message = message.replace(match.group(0), "")
            except Exception as e:
                print(f"[Error] SET_FACT 失敗: {e}")
                message = message.replace(match.group(0), f"[設定失敗: {e}]")

        # 解析 GET_FACT 動作
        get_pattern = r'<action>GET_FACT:([^<]+)</action>'
        for match in re.finditer(get_pattern, message):
            path = match.group(1).strip()

            print(f"[Debug] GET_FACT: {path}")

            try:
                value = fact_graph_client.get_fact(path)

                # 格式化數字
                if isinstance(value, (int, float)) and value > 100:
                    formatted_value = f"${value:,.0f}"
                elif isinstance(value, bool):
                    formatted_value = "是" if value else "否"
                else:
                    formatted_value = str(value)

                message = message.replace(match.group(0), formatted_value)
            except Exception as e:
                print(f"[Error] GET_FACT 失敗: {e}")
                message = message.replace(match.group(0), f"[查詢失敗: {e}]")

        # 清理多餘空行
        message = re.sub(r'\n{3,}', '\n\n', message)
        message = message.strip()

        return message
