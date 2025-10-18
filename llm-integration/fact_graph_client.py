"""
Fact Graph 客戶端包裝層
透過 subprocess 呼叫 Node.js 來操作 Fact Graph
"""

import subprocess
import json
import os
from typing import Any, Dict, Optional


class FactGraphClient:
    """Fact Graph 客戶端"""

    def __init__(self, demo_path: str = None):
        # 自動偵測路徑：Docker 容器內或本機
        if demo_path is None:
            if os.path.exists("/fact-graph/demo"):
                demo_path = "/fact-graph/demo"  # Docker 容器內
            else:
                demo_path = "/home/human/fact-graph/demo"  # 本機開發

        self.demo_path = demo_path
        self.fg_js_path = os.path.join(demo_path, "fg.js")
        self.xml_path = os.path.join(demo_path, "all-facts.xml")

        # 檢查檔案是否存在（使用 Mock 模式，不強制要求檔案）
        self.mock_mode = True
        if os.path.exists(self.fg_js_path) and os.path.exists(self.xml_path):
            self.mock_mode = False
            print(f"✅ Fact Graph 檔案找到: {self.demo_path}")
        else:
            print(f"⚠️  Fact Graph 檔案未找到，使用 Mock 模式")
            print(f"   嘗試路徑: {self.demo_path}")

        # 初始化內部狀態（用於 Mock 模式）
        self._state = {}

        # 初始化 Fact Graph
        self._init_graph()

    def _init_graph(self):
        """初始化 Fact Graph (載入 XML)"""
        # 這裡簡化處理,實際上需要啟動一個 Node.js 進程
        # 並保持連線來操作 Fact Graph
        print(f"[FactGraphClient] 初始化完成")
        print(f"[FactGraphClient] XML 路徑: {self.xml_path}")

    def set_fact(self, path: str, value: Any) -> Dict:
        """
        設定一個 Fact

        Args:
            path: Fact 路徑 (如 /filingStatus)
            value: 值 (如 "single")

        Returns:
            設定結果
        """
        print(f"[FactGraph] SET {path} = {value}")

        # 轉換布林值字串
        if isinstance(value, str):
            if value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False

        # 儲存到內部狀態
        self._state[path] = value

        # 簡化實作: 直接返回成功
        # 實際上需要呼叫 Node.js
        return {
            "success": True,
            "path": path,
            "value": value
        }

    def get_fact(self, path: str) -> Any:
        """
        查詢一個 Fact

        Args:
            path: Fact 路徑

        Returns:
            Fact 的值
        """
        print(f"[FactGraph] GET {path}")

        # 如果是推導值，計算它
        if path == "/standardDeduction":
            filing_status = self._state.get("/filingStatus", "single")
            standard_deduction_map = {
                "single": 14600,
                "married_filing_separately": 14600,
                "married_filing_jointly": 29200,
                "qualifying_surviving_spouse": 29200,
                "head_of_household": 21900
            }
            return standard_deduction_map.get(filing_status, 14600)

        elif path == "/hasAdvancedPtc":
            # /hasAdvancedPtc 是 /writableHasAdvancedPtc 的推導值
            return self._state.get("/writableHasAdvancedPtc", False)

        # 否則從狀態中取得
        return self._state.get(path, "未設定")

    def get_all_paths(self) -> list:
        """取得所有可用的 Fact 路徑"""
        # 簡化: 返回常用路徑
        return [
            "/filingStatus",
            "/standardDeduction",
            "/writableHasAdvancedPtc",
            "/hasAdvancedPtc",
            "/refundViaAch",
            "/payViaAch"
        ]

    def get_current_graph(self) -> Dict:
        """取得當前的完整圖譜資料"""
        result = {}

        # 將內部狀態轉換為 Fact Graph 格式
        for path, value in self._state.items():
            if isinstance(value, bool):
                result[path] = {"$type": "BooleanWrapper", "item": value}
            elif isinstance(value, str):
                result[path] = {"$type": "EnumWrapper", "item": {"value": value}}
            elif isinstance(value, (int, float)):
                result[path] = {"$type": "NumberWrapper", "item": value}
            else:
                result[path] = value

        return result


# 測試用
if __name__ == "__main__":
    client = FactGraphClient()

    # 測試設定
    result = client.set_fact("/filingStatus", "single")
    print(f"設定結果: {result}")

    # 測試查詢
    value = client.get_fact("/standardDeduction")
    print(f"查詢結果: {value}")

    # 取得所有路徑
    paths = client.get_all_paths()
    print(f"可用路徑: {paths}")
