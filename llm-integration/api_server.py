"""
FastAPI 伺服器
提供 REST API 和 WebSocket 介面
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
import os

from fact_graph_client import FactGraphClient
from llm_agent import TaxAssistant

# 初始化 FastAPI
app = FastAPI(title="Fact Graph + LLM API")

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 掛載靜態檔案
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# 初始化服務
try:
    fact_graph = FactGraphClient()
    print("✅ Fact Graph 客戶端初始化成功")
except Exception as e:
    print(f"❌ Fact Graph 客戶端初始化失敗: {e}")
    fact_graph = None

# 初始化 LLM 助理 (全域實例，保留對話歷史)
try:
    assistant = TaxAssistant()
    print("✅ LLM 助理初始化成功")
except Exception as e:
    print(f"❌ LLM 助理初始化失敗: {e}")
    print(f"   請確認 GOOGLE_API_KEY 環境變數已設定")
    assistant = None


# === 資料模型 ===

class ChatRequest(BaseModel):
    """聊天請求"""
    message: str
    session_id: Optional[str] = "default"


class ChatResponse(BaseModel):
    """聊天回應"""
    message: str
    fact_graph_data: Optional[dict] = None


class SetFactRequest(BaseModel):
    """設定 Fact 請求"""
    path: str
    value: str


# === API 端點 ===

@app.get("/")
async def root():
    """根路徑"""
    return {
        "message": "Fact Graph + LLM API",
        "status": "running",
        "fact_graph": "ready" if fact_graph else "not available"
    }


@app.get("/chat", response_class=HTMLResponse)
async def chat_page():
    """聊天界面"""
    with open("frontend/chat.html", "r", encoding="utf-8") as f:
        return f.read()


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    聊天端點

    使用者透過自然語言與稅務系統互動
    """
    if not fact_graph:
        raise HTTPException(status_code=503, detail="Fact Graph 未就緒")

    if not assistant:
        raise HTTPException(status_code=503, detail="LLM 助理未就緒，請檢查 API Key")

    try:
        print(f"[API] 收到訊息: {request.message}")

        # 處理訊息
        response_message = await assistant.chat(request.message, fact_graph)

        print(f"[API] 回應: {response_message[:100]}...")

        # 取得當前圖譜狀態
        current_graph = fact_graph.get_current_graph()

        return ChatResponse(
            message=response_message,
            fact_graph_data=current_graph
        )

    except Exception as e:
        print(f"[API Error] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}")


@app.post("/api/fact/set")
async def set_fact(request: SetFactRequest):
    """直接設定 Fact 值"""
    if not fact_graph:
        raise HTTPException(status_code=503, detail="Fact Graph 未就緒")

    try:
        result = fact_graph.set_fact(request.path, request.value)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/fact/get/{path:path}")
async def get_fact(path: str):
    """查詢 Fact 值"""
    if not fact_graph:
        raise HTTPException(status_code=503, detail="Fact Graph 未就緒")

    try:
        value = fact_graph.get_fact(f"/{path}")
        return {"path": f"/{path}", "value": value}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/facts/all")
async def get_all_facts():
    """取得所有可用的 Fact 路徑"""
    if not fact_graph:
        raise HTTPException(status_code=503, detail="Fact Graph 未就緒")

    paths = fact_graph.get_all_paths()
    return {"paths": paths, "count": len(paths)}


@app.get("/api/graph/current")
async def get_current_graph():
    """取得當前圖譜狀態"""
    if not fact_graph:
        raise HTTPException(status_code=503, detail="Fact Graph 未就緒")

    graph_data = fact_graph.get_current_graph()
    return {"graph": graph_data}


# === WebSocket 端點 ===

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket 聊天端點"""
    await websocket.accept()

    assistant = TaxAssistant()

    try:
        while True:
            # 接收訊息
            data = await websocket.receive_text()

            # 處理訊息
            response = await assistant.chat(data, fact_graph)

            # 發送回應
            await websocket.send_json({
                "message": response,
                "graph": fact_graph.get_current_graph() if fact_graph else {}
            })

    except WebSocketDisconnect:
        print("WebSocket 連線已斷開")


# === 啟動資訊 ===

@app.on_event("startup")
async def startup_event():
    """啟動時執行"""
    print("\n" + "="*50)
    print("🚀 Fact Graph + LLM API 已啟動")
    print("="*50)
    print(f"📖 API 文檔: http://localhost:8000/docs")
    print(f"🔌 WebSocket: ws://localhost:8000/ws/chat")
    print("="*50 + "\n")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
