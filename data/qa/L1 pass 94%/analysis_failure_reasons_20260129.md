# data/qa/step4_final_20260129_105749.csv 失敗項目分析

在檔案中偵測到 2 個 FAIL 項目，以下為詳細原因分析：

## 1. BB Ratio for 2024-12 (Item #19)

- **問題 (Question)**: "What is the BB Ratio for 2024-12?"
- **評分 (Grade)**: **FAIL**
- **預期答案 (Expected)**: 0.83
- **Agent 回答 (Agent Answer)**: Value Ratio: 1.31, Volume Ratio: 1.10
- **失敗原因分析**:
  1.  **數值與定義嚴重偏離 (Misalignment)**: Agent 計算出的數值 (1.31) 與 Ground Truth (0.83) 差異過大，顯示 Booking 或 Billing 的數據範圍判定有誤。
  2.  **指標定義不明確**: Agent 回傳了兩個指標 (金額與數量)，但題目僅詢問 "BB Ratio" (通常指金額)。Ground Truth 期望單一精確數值。
  3.  **過濾條件執行疑慮**: 評測系統指出 Agent "未能一致地應用 2024-12 過濾條件" (does not consistently apply the required 2024-12 filters)。雖然 Agent 的 SQL 文字紀錄顯示有加上日期過濾，但最終計算出的 1.31 數值暗示可能在執行時包含了錯誤的資料範圍 (例如未正確排除非 SHIPMENT 的 Billing，或 Booking 範圍過大)。

## 2. POA BB Qty Ratio MoM (Item #20)

- **問題 (Question)**: "What is the POA BB Qty Ratio for 2024-12 on a MoM basis (vs 2024-11)?"
- **評分 (Grade)**: **FAIL**
- **預期答案 (Expected)**: ~0.60 (MoM Delta ~0.05 / Growth ~8.57%)
- **Agent 回答 (Agent Answer)**: 1.0453
- **失敗原因分析**:
  1.  **邏輯理解錯誤 (Logic Error)**: 題目要求的是 **MoM (月對月) 的變化基礎** (on a MoM basis)，即比較 "12月的比率" 與 "11月的比率"。
  2.  **SQL 聚合方式錯誤**:
      - Agent 的 SQL 將 11月 與 12月 的資料 **合併加總** (`WHERE year_month IN ('2024-12', '2024-11')`)，然後計算出一個 "11+12月總合的 Booking/Billing 比率"。
      - 正確做法應分別計算 11 月與 12 月的 Ratio，再計算兩者間的成長率或差異。
  3.  **結果解釋錯誤**: Agent 將合併後的比率 (1.0453) 直接作為答案，完全忽略了 MoM 成長率的計算需求。

---

### 總結
主要失敗原因集中在 **指標定義的精確度** (Item 1 數值偏差) 與 **複雜時間邏輯的理解** (Item 2 誤將 MoM 理解為合併計算)。建議在 Prompt 中加強對於 "MoM basis" 計算邏輯的引導，並檢查 BB Ratio 計算時的資料源過濾是否嚴謹。
