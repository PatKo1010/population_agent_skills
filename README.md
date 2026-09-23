# Taiwan Population Agent

透過 Hermes Agent skills 分析臺灣「縣市人口數按性別及年齡」的 `.xls` 資料。專案把檔案檢查、資料正規化、驗證與查詢分成四個階段，由 pipeline skill 負責接續執行，最後使用固定查詢程式的結果回答問題。

## Skills 與執行流程

```text
taiwan-population-pipeline
  └─ profiler → normalizer → validator → analyst → 回答
```

| Skill | 用途 | 主要產物／通過條件 |
| --- | --- | --- |
| [taiwan-population-pipeline](.hermes/skills/taiwan-population-pipeline/SKILL.md) | 人口分析的主要入口；保留問題條件，依序執行下列四個 skills，檢查產物並處理失敗。 | 各階段通過後才回答；任何階段失敗就停止後續分析。 |
| [taiwan-population-xls-profiler](.hermes/skills/taiwan-population-xls-profiler/SKILL.md) | 檢查工作表、月份、表頭、年齡欄位、地區與缺少來源合計列等異常。 | `profile.json`；確認月份、0–99 歲、唯一的 `100+` 候選欄與地區。分析任務成功後必須接續 pipeline。 |
| [taiwan-population-normalizer](.hermes/skills/taiwan-population-normalizer/SKILL.md) | 將 XLS 轉成一致的資料結構，處理民國日期、地區層級、男女及年齡資料。 | `population_long.csv`、`population.sqlite`、`dataset_manifest.json`；保留原始 XLS 不變。 |
| [taiwan-population-validator](.hermes/skills/taiwan-population-validator/SKILL.md) | 檢查 manifest、資料庫完整性、月份、性別、年齡覆蓋與人口合計一致性。 | `validation.json`；只有 `passed` 或 `passed_with_warnings` 可進入分析，`failed` 必須停止。 |
| [taiwan-population-analyst](.hermes/skills/taiwan-population-analyst/SKILL.md) | 先確認問題能否由資料回答，再將條件轉成受限 JSON intent，由固定程式執行 SQL。 | `intent.json` 與查詢 JSON；pipeline 儲存為 `query_result.json`。只有 `status: ok` 的有效結果可作為人口數值答案。 |

[AGENTS.md](AGENTS.md) 是專案層級的流程指示：分析必須走 pipeline，不能改用直接讀取 Excel、自行計算或臨時 SQL 回答。這是 agent 的行為規範，目前沒有程式層級的 pipeline runner 或工具存取封鎖。

## 安裝專案需要的相關環境

以下終端指令以 macOS、Linux 或 Windows WSL 的 Bash 為例，請在專案根目錄執行。

### 1. 準備工具與資料

- **Git**：取得專案及讓 Hermes 識別專案技能所在的 Git repository。
- **Python 3 與 venv / pip**：執行資料處理腳本。專案目前沒有宣告最低 Python 版本；本地開發環境使用 Python 3.14。
- **Hermes Agent 與可用的模型設定**：使用 skills 時需要；單獨執行 Python 腳本與測試不需要模型金鑰。
- **來源 `.xls`**：自行準備符合此專案格式的工作簿，執行時提供絕對路徑。現有輸出檔不能取代 pipeline 所需的原始來源。

尚未安裝 Hermes 時，依照 [Hermes 官方安裝說明](https://hermes-agent.nousresearch.com/docs/getting-started/installation) 安裝，並依 [Quickstart](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart) 完成模型供應商設定。模型憑證由 Hermes 管理，不要放入專案檔案。

確認目前終端可以找到工具：

```bash
git --version
python3 --version
hermes --help
```

### 2. 建立 Python 虛擬環境並安裝套件

進入下載或 clone 後的專案資料夾：

```bash
cd /path/to/population_agent
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r .hermes/skills/requirements.txt
```

`/path/to/population_agent` 請換成實際路徑。不要沿用其他電腦複製過來的 `.venv`，應在自己的環境建立。

目前執行期唯一的第三方相依套件是 `xlrd==2.0.1`，用來讀取舊版 Excel `.xls`。CSV、JSON、SQLite 與測試所需的 `unittest` 都使用 Python 標準函式庫；不需要安裝 Excel、pandas、資料庫伺服器或 pytest。

確認 Python 使用正確環境且相依套件可匯入：

```bash
python -c "import sys, xlrd, sqlite3; print(sys.executable); print('xlrd:', xlrd.__version__); print('SQLite:', sqlite3.sqlite_version)"
```

### 3. 在 Hermes 啟用專案 skills

本專案已包含 `.hermes/skills/`，不用再從壓縮檔複製。先確認信任這個專案的技能內容，再從專案根目錄執行：

```bash
hermes skills trust
hermes
```

Hermes 的專案 skills 需要信任後才會載入，詳見 [官方 Skills System](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills)。若 Hermes 已在執行，新增或修改 skills 後請重新啟動。保留根目錄的 `AGENTS.md`，讓 agent 同時取得流程規範。

Agent 的 terminal 必須能存取來源檔與專案虛擬環境。新終端執行 `source .venv/bin/activate` 後再啟動 Hermes；若 agent 使用不同 shell、容器或遠端執行環境，需在該環境安裝相依套件，或明確指定可存取的 `/absolute/path/population_agent/.venv/bin/python` 執行腳本。

## 開始分析

在 Hermes 輸入以下指令，將來源與輸出路徑換成自己的路徑：

```text
/taiwan-population-pipeline 使用 /absolute/path/data.xls，回答 2025 年 12 月各縣市男女合計、65 歲以上（含 100+）人口占比前 10 名，輸出到 /absolute/path/output。執行 Python 腳本請使用 /absolute/path/population_agent/.venv/bin/python。
```

正常流程會產生：

```text
output/
├── profile.json
├── population_long.csv
├── population.sqlite
├── dataset_manifest.json
├── validation.json
├── intent.json
└── query_result.json
```

建議不同來源使用不同輸出資料夾；normalizer 會重建指定目錄內的資料庫。月份、地區、性別等必要條件不完整時，agent 會先詢問，不會自行改換條件。

如果只想檢查格式，請明確限定範圍：

```text
/taiwan-population-xls-profiler 僅檢查 /absolute/path/data.xls 的結構與異常，不進行人口分析。
```

## Demo 問答

以下五題選自現有 [問答輸出](outputs/golden_set_114/answers.json)，答案已與 [20 題 Golden Set](outputs/golden_set_114/golden_set_20.json) 核對一致。這是既有結果的展示，不代表本次文件更新重新執行了完整管線。民國 114 年為西元 2025 年，人口數均指指定月份的月底人口。

| 題號 | 問題 | 答案 |
| --- | --- | --- |
| G001 | 民國114年1月底，全國不分性別、全年齡人口共有多少人？ | 23,396,049 人 |
| G004 | 民國114年1月底，臺北市男性的全年齡人口是多少人？ | 1,173,374 人 |
| G008 | 民國114年1月底，全國不分性別的0歲人口是多少人？ | 130,123 人 |
| G009 | 民國114年11月底，全國不分性別65歲以上（含100歲以上）人口是多少人？ | 4,657,796 人 |
| G012 | 民國114年12月底，全國女性全年齡人口占全國不分性別全年齡總人口百分之多少？四捨五入至小數點後2位。 | 50.80% |

0 歲人口是月底的居民人口存量，不能當作當年出生人數；女性占比的分母為男女合計的全年齡人口。

## 支援範圍與目前限制

- 支援人口數查詢、排名、年齡人口占比及指定月份的時間序列；精確欄位見 [intent schema](.hermes/skills/taiwan-population-analyst/references/intent-schema.md)。
- 支援男、女與男女合計，以及單歲 0–99 歲和 `100+`；無法拆出 100 歲以上的個別歲數。
- 查詢月份必須存在於 manifest；全年人口問題需指定快照月份，不會自行選擇年底。
- 目前 profiler 的月份辨識寫死為民國 114 年（2025）；validator 要求 12 個月。其他年份、部分月份或不同版型需要先調整程式，不能假設可直接套用。
- 目前讀取 `.xls`，不支援直接輸入 `.xlsx`。
- 出生事件、遷徙人數、所得、職業與人口變化原因不在此資料集範圍；完整界線見 [query policy](.hermes/skills/taiwan-population-analyst/references/query-policy.md)。

## 驗證環境與執行測試

啟用虛擬環境後執行：

```bash
python -m unittest discover -s tests -v
```

測試涵蓋 manifest 與 query intent 行為，使用測試資料，不代表實際來源 XLS 已通過驗證。實際分析仍須經過完整 pipeline。

| 問題 | 處理方式 |
| --- | --- |
| `No module named xlrd` | 使用執行腳本的同一個 Python 執行 `python -m pip install -r .hermes/skills/requirements.txt`，並確認 agent 使用該環境。 |
| 找不到 skills | 確認從專案根目錄啟動 Hermes、已執行 `hermes skills trust`，再重新啟動。 |
| validator 回傳 `failed` | 查看 `validation.json` 的 `errors` 與 `checks`，修正資料或解析問題後重跑；不要跳過驗證。 |
| 查詢回傳非 `ok` | 依回傳 code 補齊條件或確認資料覆蓋範圍；`results: null` 不等於人口為零。 |

更多測試提問見 [TEST_QUESTIONS.md](.hermes/skills/TEST_QUESTIONS.md)。

## Pipeline 設計的優點

- **分階段定位問題**：profiler、normalizer、validator 與 analyst 各自負責檔案結構、資料轉換、品質檢查與查詢，能區分解析錯誤、資料異常及 intent 錯誤，減少排查範圍。
- **在回答前檢查資料品質**：流程要求確認月份、年齡覆蓋、性別與人口合計，再進行查詢，降低缺漏資料或重複加總造成錯誤答案的機會。驗證通過表示符合已實作的檢查，並不保證所有來源語意都正確。
- **讓模型與計算分工**：模型負責理解問題並產生受限 intent，人口計算由固定、參數化的 SQL 執行；同一份資料與相同 intent 可重現相同查詢結果。
- **保留可追溯的產物**：profile、manifest、validation、intent 與 query result 分別記錄資料結構、覆蓋範圍、驗證狀態與查詢條件，方便人工稽核與 Golden Set 比對。
- **明確處理不可回答的問題**：缺少條件、月份不存在、年齡精度不足或資料不包含出生／遷徙事件時，以結構化狀態回報，避免把缺資料當成零或任意替換條件。

目前階段順序與驗證關卡主要由 skill 和 `AGENTS.md` 規範 agent 執行；後續可增加程式化 runner，將產物關聯與通過條件落實為執行檢查。

## Intent Schema 後續改進方向

目前已支援單一地區占比的 `region`、分母性別 `denominator_sex`，以及排名方向 `order` 與並列選項 `include_ties`。以下是尚可改善的部分，不表示這些功能已完成：

| 改進方向 | 現有問題或限制 | 建議做法 |
| --- | --- | --- |
| 以機器可讀 schema 統一契約 | Markdown 說明與 Python 欄位驗證需分別維護，容易產生落差。 | 新增版本化 JSON Schema，讓 intent 產生端先做型別、必填欄位與操作別檢查，並以測試確認與執行器一致。 |
| 明確表達年齡上界 | 年齡區間必須提供 `include_100_plus`；即使問題明確為0–14歲或65–99歲，模型漏填仍會失敗。 | 提供有限區間與開放上界的標準模板；若調整預設值，只在明確有限上界時推導不含100+，語意不明時仍須澄清。 |
| 區分 intent 格式錯誤與使用者資訊不足 | `MISSING_REQUIRED_FIELDS` 可能是模型漏填，也可能是使用者未指定條件。 | 錯誤回覆列出缺少欄位與修復提示；允許依原問題補回已明確提供的條件，禁止為了成功執行而更改問題範圍。 |
| 定義查詢結果 schema | 排名結果使用 `region_name`；若答案組裝端讀取 `region`，可能出現 `Exception: 'region'`，僅修改輸入 schema 無法解決。 | 定義輸出欄位、型別與單位，統一答案組裝介面，加入從 intent 到最終文字答案的整合測試。 |
| 支援固定的跨月差額操作 | 現有 `population_trend` 僅回傳快照，未提供正式的差額運算。 | 新增受限差額操作，要求起訖月份及一致的人口條件，由程式回傳前值、後值及帶正負號的差額，避免模型自行計算。 |
| 統一百分比精度與捨入規則 | 查詢目前回傳小數點後4位百分比，題目可能要求2位；答案端再次捨入可能產生邊界誤差。 | 定義受限的精度參數與捨入規則，由查詢程式從原始分子、分母直接計算指定精度，並保留兩者供核對。 |

後續驗證應同時涵蓋有效 intent、錯誤 intent、並列排名、零分母及捨入邊界，並以完整20題測試「自然語言 → intent → 查詢結果 → 最終答案」，避免只通過單元測試卻在答案組裝階段失敗。
