# Auto Agent - Fabric Data Agent 自動化專案

這是一個針對 Microsoft Fabric Data Agent 的自動化開發與部署架構。此專案採用 SOTA (State-of-the-Art) 的 Python 專案結構，將程式碼、設定與文檔分離，以簡化開發與維護流程。

## 📁 專案結構

```
auto_agent/
├── config/                  # 設定檔案
│   ├── agent_config.json    # 編譯後的 Agent 設定
│   └── test_queries.json    # 測試用的自然語言查詢
├── data/                    # 數據與日誌
│   └── logs/                # 執行日誌 (run_logs.json)
├── docs/                    # 文件與 Prompt
│   ├── prompts/             # AI 指令與 Data Source 說明
│   │   ├── AI_Instructions.md
│   │   └── data_instructions.md
│   └── SOTA_Response_Plan.md
├── scripts/                 # 自動化工具腳本
│   ├── deploy.py            # [核心] 編譯設定並部署至 Fabric OneLake
│   └── sync.py              # 同步執行日誌
├── src/                     # 原始碼
│   └── auto_agent/
│       └── fabric_runner.py # Fabric Notebook 執行邏輯
└── tests/                   # 測試程式碼
```

## 🚀 快速開始

### 1. 環境準備
請確保已安裝 Python，並安裝必要的 Azure SDK 套件：

```bash
pip install azure-storage-file-datalake azure-identity
```

### 2. 開發流程
我們的開發流程已簡化為「修改文件 -> 一鍵部署」。

1.  **修改指令 (Prompt Engineering)**:
    *   編輯 `docs/prompts/AI_Instructions.md` 來調整 AI 的行為與角色設定。
    *   編輯 `docs/prompts/data_instructions.md` 來定義資料庫 Schema 與 Few-Shot Examples。

2.  **部署至 Fabric (Compile & Deploy)**:
    執行 `deploy.py` 腳本。此腳本會自動將 Markdown 文件編譯為 JSON 設定檔，並連同程式碼一起上傳至 Fabric OneLake。

    ```bash
    python scripts/deploy.py
    ```

3.  **在 Fabric 上執行**:
    在 Microsoft Fabric 的 Notebook 中執行 `fabric_runner.py` (或是透過 Pipeline 觸發)。

4.  **同步執行結果 (Sync Logs)**:
    執行完畢後，使用 `sync.py` 將日誌下載到本地進行分析。

    ```bash
    python scripts/sync.py
    ```
    日誌將儲存於 `data/logs/run_logs.json`。

## 🛠️ 腳本說明

- **scripts/deploy.py**:
    - **編譯功能**: 讀取 `docs/prompts/` 下的 Markdown 文件，處理截斷 (Truncation) 與格式化，生成 `config/agent_config.json`。
    - **部署功能**: 使用 Azure ADLS Gen2 API 直接將設定檔與程式碼上傳至指定的 OneLake 路徑 (`/Files/data_agent`)，無需等待 OneDrive 同步。

- **scripts/sync.py**:
    - 從 OneLake 下載最新的執行日誌，並顯示簡易的執行摘要（成功/失敗的查詢數量）。

## 📝 注意事項

- 本專案依賴 Azure CLI 或瀏覽器驗證 (InteractiveBrowserCredential) 進行權限認證，執行腳本時請留意彈出的登入視窗。
- 上傳目標路徑設定於腳本中的 `ONELAKE_URL` 與 `WORKSPACE_NAME` 變數，請根據實際環境進行調整。
