# Sales Data Agent Prompt SOTA 重構報告

本報告旨在確認 Agent System Prompts 的邏輯完整性、格式合規性，以及重構後的架構分類。

## 1. 邏輯完整性驗證 (Logic Integrity Check)

經過與備份版本 (`_bk20260210`) 的比對，確認所有關鍵商業邏輯皆已**完整遷移**且無遺漏：

| 邏輯類別 | 原始位置 | 新位置 | 狀態 |
| :--- | :--- | :--- | :--- |
| **商業公式 (Business Formulas)** | `agent_instructions.md` (Sec 2) | **`data_instructions.md` (Sec 4)** | ✅ 完整遷移 (BB Ratio, Hit Rate, GM%, ASP) |
| **時間邏輯 (Temporal Logic)** | `agent_instructions.md` (Sec 4.3) | **`data_instructions.md` (Sec 4.4)** | ✅ 完整遷移 (MTD, QTD, YTD, Last N Months Proxy) |
| **實體解析 (Entity Resolution)** | `agent_instructions.md` (Sec 5) | **`data_instructions.md` (Sec 3.3)** | ✅ 統一使用 Data Instructions 的 SOTA Triple-Net Protocol |
| **關鍵字映射 (Magic Words)** | `agent_instructions.md` (Sec 8) | **`data_instructions.md` (Sec 6)** | ✅ 完整遷移 (AI Proxy, Sensor Synergy, Zombie Backlog 等) |
| **CTE sql 寫法** | `agent_instructions.md` (Sec 4) | **`data_instructions.md` (Sec 4)** | ✅ 完整遷移 (MoM, Hit Rate CTE Pattern) |
| **美金單位 (USD Currency)** | (新增) | **`data_instructions.md` (Sec 1)** | ✅ 已明確定義 |

**結論**：所有 "Hard Logic" (硬邏輯) 已全數歸位至 `data_instructions.md`，解決了 "Split Brain" (邏輯分裂) 問題。

## 2. 格式與字數限制檢查 (Format & Limit Check)

根據 `prompts/agent/README.md` 的規範：

| 文件 | 限制 (字元) | 當前預估字元數 | 狀態 |
| :--- | :--- | :--- | :--- |
| **Agent Instructions** | 15,000 | ~5,000 (大幅瘦身) | ✅ Pass (由 ~13,000 降至 ~5,000) |
| **Data Instructions** | 15,000 | ~11,000 (增加但未超標) | ✅ Pass (由 ~9,000 增至 ~11,000) |

**結論**：重構後的 Prompt 結構更為均衡，且遠低於 Token 上限，留有充足的擴充空間。

## 3. SOTA 架構分類整理 (Restructuring Classification)

本次重構採用 **"權責分離 (Separation of Concerns)"** 策略，將 Agent 的腦袋分為「知識庫」與「行為準則」：

### 📘 Data Instructions (知識庫 / The "WHAT")
*   **定義 (Definitions)**: 資料表Schema、欄位定義、美金單位。
*   **邏輯 (Logic)**: 所有的商業公式 (Hit Rate, BB Ratio)、時間計算 (Latest Closed Month)、實體解析規則 (Triple-Net)。
*   **字典 (Dictionary)**: 關鍵字映射表 (Magic Words)、產品/客戶清單。
*   **技能 (Skills)**: 特定的 SQL 寫法模式 (CTE Isolation Pattern)。

### 📙 Agent Instructions (行為準則 / The "HOW")
*   **人設 (Identity)**: SBG Strategy Assistant 的角色設定。
*   **輸出 (Output)**: 強制性的 Executive Summary 格式 (Opening Hook, Structured Details)。
*   **原則 (Principles)**: KISS 原則 (SQL 簡潔化)、Business Neutrality (客觀陳述)。
*   **互動 (Interaction)**: 遇到模糊問題的應對、如何參照 Data Instructions。

---

**最終效益**：
1.  **維護性提升**：修改公式只需改一份文件 (`data`)。
2.  **穩定性提升**：Agent 不再因為兩邊邏輯些微不同而產生幻覺。
3.  **Token 效率**：消除了大量重複文本。
