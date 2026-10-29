# 不用 DSP-1 的 Pilotwings

一套工具，為全部三個地區版本建置 Pilotwings 映像檔，以卡帶內的表格和 65816 程式碼取代 DSP-1 協處理器。遊戲問甚麼以零售版卡帶為準，每個答案以晶片本身的微碼為準。

[English](README.md) | [日本語](README.ja.md) | [简体中文](README.zh-Hans.md) | 繁體中文（香港）

[![ci](https://img.shields.io/github/actions/workflow/status/gufranco/snes-pilotwings-nochip/ci.yml?branch=main&style=flat-square&label=ci)](https://github.com/gufranco/snes-pilotwings-nochip/actions/workflows/ci.yml)
[![release](https://img.shields.io/github/v/release/gufranco/snes-pilotwings-nochip?style=flat-square&label=release)](https://github.com/gufranco/snes-pilotwings-nochip/releases/latest)
[![coverage](https://img.shields.io/badge/coverage-100%25-brightgreen?style=flat-square)](https://github.com/gufranco/snes-pilotwings-nochip/actions/workflows/ci.yml)
[![license](https://img.shields.io/github/license/gufranco/snes-pilotwings-nochip?style=flat-square&label=license)](LICENSE)

**16** 個指令在 **3** 份地區錄製記錄所含的每個問題上與晶片對照作答，**0** 個錯誤答案，**43,440** 個 `$0a` 地面字中 **43,440** 個完全正確，**1,093** 個測試，每個模組的陳述式和分支覆蓋率均為 **100%**，除標準函式庫外沒有任何依賴，另有 **5** 個固定版本的子模組

```python
import tables
import tabulate

for one in tables.KNOWN:
    print(f"{one.name:10} {one.count:3} words  first {one.values()[:3]}")
print(tables.table_bytes(), "bytes for all four")

for words in (1, 2, 3):
    print(words, f"{tabulate.bytes_for(words):,}", tabulate.storable(words))
```

```
reciprocal 128 words  first (32767, 32514, 32264)
sine       128 words  first (0, 804, 1607)
cosine     128 words  first (32767, 32758, 32728)
arccosine  256 words  first (16384, 16343, 16303)
1280 bytes for all four
1 131,072 True
2 8,589,934,592 False
3 562,949,953,421,312 False
```

第一個迴圈按公式重建 DSP-1 存放在數據 ROM 中的四個表格，[`tables.py`](tables.py) 正是在微碼中搜尋這些表格。第二個迴圈計算一個表格的大小，該表格存放讀取一個、兩個或三個參數字的指令的全部答案：一個字可放進 96 Mbit 卡帶，兩個字則放不下。這一行正是替代方案只儲存遊戲所問的答案、其餘則即時計算的原因。

## 安裝

### 逐步操作

由零開始到可用的副本共五步。第 4 步的 doctor 會確認前三步。

1. **只安裝 git 和 Docker。** Python 以及建構用到的每個工具都在本專案的 Docker 映像裏，第一個指令會建構它。

   | | Windows | macOS | Linux |
   |:--|:--|:--|:--|
   | git | `winget install Git.Git` | `xcode-select --install` | 發行版的 `git` 套件 |
   | Docker | `winget install Docker.DockerDesktop`，然後啟動 Docker Desktop | Docker Desktop，或 `brew install colima docker` 後執行 `colima start` | Docker Engine，然後 `sudo systemctl start docker` |

   在 Windows 上，本頁寫 `./run.sh` 的地方請輸入 `.\run.cmd`。

2. **複製儲存庫，不要下載。**

   ```bash
   git clone --recurse-submodules https://github.com/gufranco/snes-pilotwings-nochip.git
   cd snes-pilotwings-nochip
   ```

   > [!CAUTION]
   > 只有複製才能得到可用的副本。GitHub 上綠色的 **Code** 按鈕亦提供 **Download ZIP**，但 ZIP 在這裏永遠無法使用：本專案依賴的 5 個模型是以 git 子模組固定的獨立倉庫，ZIP 一個都不包含，之後亦無法補上。啟動腳本會拒絕這樣的副本並說明原因；請刪除它並複製。沒有加 `--recurse-submodules` 的複製，可以用 `git submodule update --init --recursive` 就地修復。

3. **把傾印檔放進 `external/roms/`**，檔名按[傾印檔清單](#the-dumps)：`pilotwings-usa.sfc`, `pilotwings-jp.sfc`, `pilotwings-eur.sfc`。微碼放在 `external/firmware/`。然後檢查，你提供的每個傾印檔都應顯示 `ok`。這第一個指令會建構映像，需時數分鐘；之後的指令會即時開始：

   ```bash
   ./run.sh tools/identify.py
   ```

4. **執行 doctor。** 它檢查副本、每個模型、每個傾印檔和映像中的工具，最後說明下一步執行甚麼：

   ```bash
   ./run.sh doctor.py
   ```

   ```
     N checks, nothing to report
     next: ./run.sh tools/identify.py, or on Windows .\run.cmd tools/identify.py
   ```

   標有 `!` 的行，下一行寫着該怎麼做。doctor 和啟動腳本能發現的設定錯誤：

   | 提示 | 怎樣做 |
   |:--|:--|
   | `This folder has no git metadata` | 刪除資料夾並複製，第 2 步 |
   | `Docker is not installed` | 第 1 步 |
   | `Docker is installed but its engine is not answering` | 啟動 Docker Desktop，或 `sudo systemctl start docker` |
   | `... is not checked out` | `git submodule update --init --recursive` |
   | `cartridge ...: missing` | 第 3 步 |

5. **目前還沒有單一的建構指令。** 本專案高度實驗性：它透過「介面」中的指令錄製遊戲、建構表並為映像檔打修補，預計會有很多問題。歡迎報告。

### 所需項目與 doctor

| 需求 | 版本 |
|:--|:--|
| git | 任何版本，用於取得五個子模組 |
| 你自己的卡帶傾印檔 | 每個 524,288 位元組，放在 `external/roms/` 中，檔名見[傾印檔](#the-dumps) |
| 你自己的 DSP-1 微碼副本 | 8,192 位元組，存為 `external/firmware/dsp1.bin` 和 `external/firmware/dsp1b.bin` |
| Docker | 任何現行版本，並須正在運行。Python 3.12、asar 1.81 和錄製模擬器都在 [`Dockerfile`](Dockerfile) 描述的映像中，[`run.sh`](run.sh) 在其中執行每個指令 |

除 Docker 和 git 外，不會在你的機器上安裝任何東西，執行時亦不會下載任何東西。本專案用作對照的五個模型是位於儲存庫根目錄的 git 子模組。從 download-zip 連結取得的原始碼封存檔不包含任何一個，診斷腳本會把這樣的資料夾報告為封存檔。

微碼可以放在 `UPD7725_FIRMWARE_DIR` 指定的任何位置，而不是 `external/firmware/`。沒有微碼的話，每個驅動晶片的檢查都會報告沒有東西可執行。

診斷腳本會印出機器資訊、本專案的版本、該資料夾是否為 git 複製、每個模型及其版本、微碼能否執行、兩個掩膜版本中哪些存在、每個傾印檔的狀態，以及每個模型本身的診斷腳本的報告，按該模型的名稱歸檔。所有檢查都通過時以 0 結束，否則以 1 結束。提交任何錯誤報告時請貼上完整輸出。在全新的遞迴複製中，沒有傾印檔也沒有微碼時，輸出以下列內容結尾：

```
  5 of 95 checks did not pass
  next: fix the first line marked ! above, then run ./run.sh doctor.py, or on Windows .\run.cmd doctor.py
```

這五個是：缺少的微碼、DSP 模型沒有映像檔的兩個掩膜版本，以及兩個子模組各自附帶的空 `cartridges` 目錄。

## 介面

這是一組從儲存庫根目錄執行的腳本，加上構成它們的模組。需要參數的腳本在沒有參數時會印出用法行並以 2 結束。

### 指令

| 指令 | 參數 | 作用 | 結束碼 |
|:--|:--|:--|:--|
| `./run.sh doctor.py` | 無 | 報告機器資訊和整條模型鏈 | 0 表示正常，1 表示有檢查未通過 |
| `./run.sh tools/identify.py` | 無 | 將 `external/roms/` 中每個檔案與 [`artifacts.manifest.json`](artifacts.manifest.json) 對照，並印出在 macOS、Linux 和 Windows 上計算 SHA-256 的指令 | 0 表示每個傾印檔都相符或不存在，1 表示有一個不正確 |
| `./run.sh exchanges.py <trace>` | 一份錄製記錄 | 在每個指令發出點切分錄製記錄，印出每個指令及其交換次數、佔比、不同參數組數、發出點，以及可以如何作答 | 0、2 |
| `./run.sh tables.py <microcode image>` | 一個 8,192 位元組的映像檔 | 在映像檔的數據 ROM 中找出四個表格，並印出每個表格起始的字位置 | 0、2 |
| `./run.sh microcode.py <mask>` | `dsp1` 或 `dsp1b` | 走訪微碼對全部 256 個指令位元組的分派，並印出每個處理程序及卡帶寫入的指令 | 0、2 |
| `./run.sh layout.py <image> <bytes wanted>` | 一個映像檔和一個大小 | 找出長度為 256 位元組或以上的 `$FF` 或 `$00` 連續區段，並指出映像檔能否在不擴大的情況下容納該大小 | 0、2 |
| `./run.sh lut.py [<rows>]` | 每個表格的行數，預設 65,536 | 計算四個表格在整個輸入範圍上製表後的大小 | 0 |
| `./run.sh derived.py <mask> [<directory>] [--reindex]` | 一個掩膜版本、輸出目錄，預設 `build` | 驅動晶片計算 `$4000` 至 `$7FFF` 的倒數，以及 65,536 個角度的正弦和餘弦，並為每個字計算前導倍增次數。將 `reciprocal`、`recip-up`、`recip-down`、`recip-exponent`、`leading`、`sine` 和 `cosine` 寫成 32,768 位元組的分片，命名為 `<stem>-<n>.bin`。`--reindex` 從已在磁碟上的倒數重建三個 `recip-` 表格 | 0、2 |
| `./run.sh state02build.py <mask> [<directory>]` | 一個掩膜版本、存放錄製記錄並接收輸出的目錄，預設 `build` | 在錄製記錄所含的每個參數組上驅動 `$02`，並寫出它的三個狀態表格 `state02-map.asm`、`state02-data.asm`，以及 65,536 個角度的鉗位餘弦 | 0、2 |
| `./run.sh lutbuild.py <mask> [<directory>]` | 一個掩膜版本、輸出目錄，預設 `build` | 從 `build/trace-usa.bin`、`build/trace-jp.bin` 和 `build/trace-eur.bin` 建立已錄製答案的表格，透過驅動 DSP-1 補全 `$13` 和 `$18`，並寫出 `lut-<n>.bin`、`lut-map.asm` 和 `lut-axes.asm` | 0、2 |
| `./run.sh patch.py <rom> <symbols> <out> <game bytes> [--slow]` | 組譯後的映像檔、由 `name hex` 行組成的符號檔、輸出路徑、映像檔內遊戲部分的長度 | 將卡帶對晶片的每次存取指向替代程式，從標頭中清除協處理器，設定大小位元組，除非指定 `--slow` 否則設定快速 ROM 位元，並重寫校驗和 | 0，1 表示映像檔沒有存取晶片，2 |
| `./run.sh tools/cycles.py <image> <assembler log> [<routine>] [<snapshot>]` | 一個映像檔、組譯器印出的符號，預設常式 `ground_block`，預設快照 `build/nb2/wram-000300.bin` | 在 65816 模型上執行一次該常式，並印出其週期數和指令數 | 0，1 表示沒有快照，2 |
| `./run.sh tools/profile.py <image> <symbol file> [<routine>] [<snapshot>] [--built]` | 同上，快照已含建好的表格時另加 `--built` | 執行一次呼叫，按每條指令所在的標籤拆分週期數，列出前 16 名 | 0，1 表示沒有快照或標籤，2 |

```bash
./run.sh tables.py external/firmware/dsp1.bin
```

```
  table        words   at     formula
  reciprocal     128    101  2^22 / (128 + k), rounded and clamped
  sine           128    280  sin(pi k / 128) x 32768, fraction cut off
  cosine         128    408  cos(pi k / 128) x 32768, fraction cut off
  arccosine      256    542  acos(k / 256) x 32768 / pi

  4 of 4 carried, 1,280 bytes to reproduce them all, against 131,072 for one table over a whole input
```

對 `external/firmware/dsp1b.bin` 執行同一指令，會發現正弦、餘弦和反餘弦低兩個字，位於 278、406 和 540，倒數則位於 101。

### 錄製模擬器

映像中的 `pwemu` 由 [`emu/`](emu/) 建置，即位於 commit `2971061cf07fdc6fc7d18883edf4e648eb16a6d2` 的 snes9x，在每次 DSP-1 埠存取上加了掛鈎，前面是一個最簡的 libretro 前端。

```bash
./run.sh --exec env PWTRACE=build/trace-usa.bin pwemu external/roms/pilotwings-usa.sfc 12000
```

| 輸入 | 含義 |
|:--|:--|
| `<rom> <frames>` | 映像檔和要執行的幀數 |
| `PWTRACE` | 二進制埠記錄的路徑 |
| `PWSCRIPT` | 輸入腳本，每行一個 `frame button...`，按鈕名稱為 `up`、`down`、`left`、`right`、`a`、`b`、`x`、`y`、`l`、`r`、`start` 和 `select` |
| `PWRAM` | 接收工作 RAM 中沒有任何一幀改動過的每個連續區段的路徑，格式為 `start end length` |
| `PWPC` | 接收每幀取樣一次的程式計數器的路徑 |

它以 `RESULT load=ok frames=<n> delivered=<n> accesses=<n> brightness=<x>` 結尾並以 0 結束，映像檔無法讀取或載入時以 1 結束。

埠記錄中每筆記錄為 12 位元組，小端序：32 位元的幀號、連同記憶庫的 32 位元程式計數器、16 位元的埠位址、讀取為 1 或寫入為 0，以及傳送的位元組。[`exchanges.py`](exchanges.py) 和 [`census.py`](census.py) 讀取這個格式。

[`emu/native.cpp`](emu/native.cpp) 透過在執行時載入的 libretro 核心進行同樣的錄製，用法為 `native <core> <rom> <frames>`；[`emu/play.cpp`](emu/play.cpp) 則在一個核心上開啟視窗，用法為 `play <core> <rom>`。

### 組譯器

映像中帶有由 [`Dockerfile`](Dockerfile) 建置的 asar v1.81。[`asm/nochip.asm`](asm/nochip.asm) 是入口檔案。它把替代程式放在記憶庫 `$10`，引入 [`asm/`](asm/) 中所有其他 `.asm` 檔案，並讀取上述腳本寫入 `build/` 的表格。它印出的 `SYM <name> <address>` 行正是 [`tools/cycles.py`](tools/cycles.py) 讀取的內容。

### 傾印檔、版本和底層模型

| 模組 | 呼叫 | 傳回 |
|:--|:--|:--|
| [`dumps.py`](dumps.py) | `artifacts()` | 三筆 `Artifact` 記錄：`name`、`region`、`filename`、`declares`、`accepted`、`provenance` |
| | `identify(data, digest=None)` | SHA-256 相符的 `Artifact`，或 `None` |
| | `identify_digest(digest)` | 同上，但使用已計算好的摘要 |
| | `diagnose(data, digest=None)` | 一個帶有 `kind`、`detail` 和 `repair` 的 `Finding`。`kind` 為 `match`、`copier-header`、`wrong-size` 或 `unrecognised` |
| | `digest_commands(filename)` | 用於 `macOS`、`Linux` 和 `Windows` 的 SHA-256 指令 |
| | `manifest()`, `through()`, `not_this()` | 清單、其來源，以及清單指名要拒絕的檔案 |
| [`version.py`](version.py) | `VERSION`, `stamped(name, release=None)` | 發行版本，以及該版本的映像檔所帶的檔名 |
| [`hardware.py`](hardware.py) | `install(environment=None)` | 把每個模型加入 `sys.path`，把 `external/firmware/` 加入 `UPD7725_FIRMWARE_DIR`，並傳回該變數 |
| | `load(package)` | 一個模型套件：`mos65xx`、`snesdsp`、`mapper`、`romimage`、`snesdriver` 或 `upd7725` |
| | `root_of(package)` | 模型的目錄。任何其他名稱會引發 `UnknownPackage` |
| [`tools/identify.py`](tools/identify.py) | `look(artifact, root)`, `judge(artifact, data)` | 一個 `Looked`，帶有 `region`、`filename`、值為 `ok`、`absent` 或 `wrong` 的 `state`、`detail`，以及 `ok` |

```python
import dumps
import version

for one in dumps.artifacts():
    print(one.region, one.filename, one.declares["chipset"], one.declares["map"])

for data in (bytes(524_288 + 512), bytes(1_000), bytes(524_288)):
    found = dumps.diagnose(data)
    print(found.kind, "|", found.detail)

print(version.stamped("pilotwings-usa"))
```

```
USA pilotwings-usa.sfc 0x03 0x20
Japan pilotwings-jp.sfc 0x03 0x20
Europe pilotwings-eur.sfc 0x03 0x20
copier-header | the file is 512 bytes longer than a bare dump, which is what a copier adds
wrong-size | 1,000 bytes, which is smaller than the 524,288 a dump holds
unrecognised | the right length, and its sha256 is 07854d2fef297a06ba81685e660c332de36d5d18d546927d30daad6d7fda1541, which none of the 3 declared dumps carries
pilotwings-usa-v0.1.0.sfc
```

在這裏，長度、晶片組或標題永遠不能識別傾印檔，摘要則永遠可以。

### 讀取卡帶的程式碼

| 模組 | 呼叫 | 傳回 |
|:--|:--|:--|
| [`commands.py`](commands.py) | `accesses(rom)` | 對位於 `$8000` 的數據埠或位於 `$C000` 的狀態埠的每個 `Access`，包括記憶庫 `$3F` 中的長格式和絕對格式。每個都帶有 `offset`、`mnemonic`、`size`、`register`、`way` 和 `long` |
| | `stores(rom)`, `store_at(rom, at)` | 對數據埠的儲存指令的偏移，以及某個偏移處的儲存指令 |
| | `read(rom, disassemble)` | 每個儲存指令一個 `Site`，最多往回解碼 512 位元組，帶有 `command`、`narrow`、`issues` 和 `why` |
| | `commands(sites)` | 這些發出點所發出的指令位元組，已排序 |
| [`sites.py`](sites.py) | `reached(rom)`, `census(rom)` | 長格式透過 [snes-driver-python](https://github.com/gufranco/snes-driver-python) 存取晶片的位置，以及一個含 `sites` 和 `shapes` 的 `Census` |

```python
import commands

code = bytes.fromhex("8f 00 80 3f  ad 00 c0  8d 00 80  ea  af 00 80 3f")
for one in commands.accesses(code):
    print(one, one.long)
print(commands.stores(code))
```

```
<Access $00000 sta data write long> True
<Access $00004 lda status read absolute> False
<Access $00007 sta data write absolute> False
<Access $0000b lda data read long> True
(0, 7)
```

### 讀取錄製記錄

| 模組 | 呼叫 | 傳回 |
|:--|:--|:--|
| [`exchanges.py`](exchanges.py) | `taken(trace)` | 每個 `Exchange`，在發出它的發出點切分：`site`、`command`、`words`、`answer`，以及表示答案開始後才寫入的字的 `later` |
| | `issuing(trace)` | 只寫入數據埠低半部的程式計數器，每個附帶其唯一的指令位元組 |
| | `census(trace)`, `read(path)` | 一個帶有 `commands`、`total`、`issued(c)`、`distinct(c)`、`share(c)`、`sites(c)` 和 `table_bytes()` 的 `Census` |
| | `spans(census, command)` | 每個參數位置一個 `Span`：`lowest`、`highest`、`distinct`、`width`、`bits`，以及當不同值填滿至少一半寬度時的 `dense` |
| | `readings(runs, command)` | 一個 `Reading`，指出哪個較早的指令的參數可令鍵決定答案：`carrier`、`rows`、`ambiguous`、`pure`、`tabulatable` |
| | `tier_of(command, distinct)` | `$00` 為 `computed`，最多 16 個參數組為 `inline`，超過則為 `table` |
| [`census.py`](census.py) | `taken(trace)`, `exchanges(trace)`, `report(census)` | 同一問題，但在位元組流上切分，每次讀取結束一次交換。`$0a` 會打破這種切分。只是函式庫：執行該檔案不會印出任何東西 |

```python
import struct

import exchanges


def access(pc, address, is_read, byte):
    return struct.pack("<IIHBB", 0, pc, address, is_read, byte)


def multiply(first, second, answer):
    out = access(0x00A000, 0x8000, 0, 0x00)
    for word in (first, second):
        out += access(0x00A010, 0x8000, 0, word & 0xFF)
        out += access(0x00A010, 0x8001, 0, word >> 8)
    out += access(0x00A020, 0x8000, 1, answer & 0xFF)
    out += access(0x00A020, 0x8001, 1, answer >> 8)
    return out


trace = multiply(0x1234, 0x5678, 0x0C4C) + multiply(0x1234, 0x5678, 0x0C4C) + multiply(2, 3, 0)
for one in exchanges.taken(trace):
    print(one, [hex(word) for word in one.words], [hex(word) for word in one.answer])

census = exchanges.census(trace)
print("\n".join(exchanges.report(census)))
for span in exchanges.spans(census, 0x00):
    print(span, span.width, span.dense)
```

```
<Exchange $00 from $00a000 2 words> ['0x1234', '0x5678'] ['0xc4c']
<Exchange $00 from $00a000 2 words> ['0x1234', '0x5678'] ['0xc4c']
<Exchange $00 from $00a000 2 words> ['0x2', '0x3'] ['0x0']
3 exchanges over 1 commands

  cmd   exchanges   share   distinct   sites   how to answer it
  $00           3  100.0%          2       1   computed
<Span 0 2..4660, 2 used> 4659 False
<Span 1 3..22136, 2 used> 22134 False
```

這份追蹤記錄是錄製格式中的三次 `$00` 交換。位於 `$00A000` 的發出點只向埠的低半部寫入一個位元組，因此它是指令發出點，其後的兩個字是參數。`$0C4C` 是 `$1234` 和 `$5678` 以十五個小數位元計算的有號乘積，也就是晶片給出的答案。

### 向晶片提問

這些模組透過 [snes-dsp-python](https://github.com/gufranco/snes-dsp-python) 驅動微碼，因此每個都需要機器上有微碼。

| 模組 | 呼叫 | 傳回 |
|:--|:--|:--|
| [`tabulate.py`](tabulate.py) | `shape_of(command)`, `sweep(model="dsp1")` | 一個帶有 `writes`、`reads` 和 `answers` 的 `Shape`，量度方法是每次多寫一個字，直到晶片沒有回應 |
| | `ask(command, words, reads=1)`, `deterministic(command=0)` | 答案位元組，以及兩個相同的問題是否得到相同答案 |
| | `entries_for(words)`, `bytes_for(words, out=1)`, `storable(words)` | 涵蓋整個輸入範圍的表格大小，以及它能否放進 96 Mbit 卡帶的一半。這些不需要微碼 |
| [`tables.py`](tables.py) | `KNOWN`, `carried(image)`, `find(words, table)`, `words(image)`, `table_bytes()` | 四筆 `Table` 記錄、每個在映像檔中的位置，以及它們的大小。`words` 在映像檔不是 8,192 位元組時引發 `WrongShape` |
| [`microcode.py`](microcode.py) | `program_of(mask)`, `dispatch(program)`, `handlers(program)`, `body(program, at)`, `listing(program)` | 2,048 個程式字、每個指令位元組的落點，以及從處理程序到其返回為止的指令 |
| | `ISSUED` | 卡帶寫入的 19 個指令位元組 |
| [`derived.py`](derived.py) | `reciprocal(part)`, `refined(part, value)`, `trig(part)`, `ask(part, command, words, answers)` | 晶片在 `$4000` 至 `$7FFF` 上的倒數，以及每個角度的正弦和餘弦。`refined` 在 200 條指令後仍未返回時引發 `Runaway` |
| | `leading(value)`, `counted()`, `doublings(folded)`, `inverted(mantissas, negative)` | 前導位元計數，以及為地面常式重新編排索引的倒數。`inverted` 在表格不是 16,384 個項目時引發 `ValueError` |
| | `write(where, values)`, `write_bytes(where, raw)`, `pieces(where)` | 寫入並讀回 32,768 位元組的分片。沒有任何分片時 `pieces` 引發 `FileNotFoundError` |
| [`complete.py`](complete.py) | `domains(runs)`, `wanted(values)`, `filled(command, keys, answers, have)` | `$13` 和 `$18` 每個參數取的每個值、這些值的每種組合，以及為沒有錄製記錄的組合從晶片驅動出來的答案 |
| [`routines.py`](routines.py) | `run(image, entry, words, answers)`, `asked(command, words, answers)`, `inputs(count, how_many, seed)` | 在 65816 模型上執行一個組譯後的常式、晶片對同一問題的答案，以及帶種子的隨機參數。`run` 在 40,000 條指令後引發 `TooLong` |

### 從晶片讀出的算術

| 模組 | 呼叫 | 傳回 |
|:--|:--|:--|
| [`attitude.py`](attitude.py) | `matrix(sine, cosine, five, six)` | `$02` 建立的矩陣的九個單元，以其暫存位址 `$5A` 至 `$7C` 為鍵 |
| [`raster.py`](raster.py) | `answer(state, start, lines, table)`, `scanline(state, line, table)` | `$0a` 每行的四個答案字，按晶片的計算方式計算 |
| | `product`, `normalise`, `reciprocal`, `scaled`, `shortfall(got, want)` | 各個階段，以及兩個答案有多少行相符 |
| [`parameter.py`](parameter.py) | `GROUPS`, `CELLS`, `gathered(seen, slots)`, `fixed(runs)`, `mirrored(state)`, `sized(rows)` | 每個狀態字跟隨 `$02` 的七個參數中的哪一個。一個鍵給出兩個狀態時 `gathered` 引發 `Disagreement`，矩陣不是兩個字重複兩次時 `mirrored` 引發 `NotMirrored` |
| [`state02.py`](state02.py) | `packed(table)`, `checked(table)`, `rows(table)`, `stride(table)` | 以已排序的小端序字表示的帶鍵表格。`checked` 在各行寬度不同時引發 `Ragged`，在值超出一個字時引發 `TooWide` |
| [`state02build.py`](state02build.py) | `gather(mask, where)`, `driven(part, sets)`, `tables(seen)`, `clamped(part)`, `checked(built)` | 三個狀態表格，以及其中一個超過 32,768 位元組記憶庫時的 `TooBig` |

```python
import attitude
import raster

print(raster.product(0x4000, 0x4000), raster.product(0x7FFF, -0x8000))
print(raster.normalise(0x0100), raster.normalise(-1), raster.normalise(0))
print(raster.scaled(0x2000, 14), raster.scaled(0x2000, 20), raster.scaled(0x2000, 2))

sine = [0x0000, 0x5A82]
cosine = [0x7FFF, 0x5A82]
cells = attitude.matrix(sine, cosine, 0, 1)
print({f"${at:02x}": f"${word:04x}" for at, word in cells.items()})
```

```
8192 -32767
(16384, 6) (-32768, 15) (0, 0)
4096 32767 1
{'$5a': '$5a81', '$5b': '$a57e', '$5c': '$0000', '$6a': '$5a81', '$6b': '$5a81', '$6c': '$0000', '$7a': '$0000', '$7b': '$0000', '$7c': '$7ffe'}
```

`product` 將兩個帶十五個小數位元的有號字相乘。`normalise` 向左移位直到第 15 和第 14 位元不同，並在結果旁傳回移位次數。`scaled` 套用指數並在 `$7FFF` 處鉗位。矩陣以角度 0 作為第五個參數，以正弦和餘弦均為 `$5A82` 的角度作為第六個參數建立。

```python
import state02

table = {(2, 1): (10, -1), (1, 5): (20, 30)}
print(state02.rows(table), state02.stride(table))
print(state02.packed(table).hex(" "))

try:
    state02.packed({(1,): (2,), (3, 4): (5,)})
except state02.Ragged as error:
    print(error)
```

```
2 4
01 00 05 00 14 00 1e 00 02 00 01 00 0a 00 ff ff
row (3, 4) is (2, 1), an earlier row is (1, 1)
```

各行按鍵排序，讓卡帶以二分法找到某一行；每行由其鍵字和隨後的答案字組成。

### 表格、映像檔和修補

| 模組 | 呼叫 | 傳回 |
|:--|:--|:--|
| [`lutbuild.py`](lutbuild.py) | `rows_of(runs)`, `completed(built, runs)`, `chosen(built, calls, room)`, `gather(where)` | 每個指令的已錄製答案，在晶片保存狀態處以 `CARRIER` 為鍵，`$13` 和 `$18` 已補全，其餘按每位元組呼叫次數挑選 |
| | `encode(tables)`, `sliced(raw)`, `banks(pieces, first)`, `source(pieces, first_bank)` | 卡帶讀取時的表格形式，切分成從 `$99` 開始並跳過 `$7E` 和 `$7F` 的記憶庫。某行會從奇數位元組開始時 `encode` 引發 `Uneven` |
| | `axes(built)`, `axes_source(found)` | 鍵為其所有值的每種組合的指令，以及以計算行號代替搜尋的程式碼 |
| | `CARRIER`, `COMPUTED`, `UNSTORABLE` | 載體、以算術作答的指令 `$00`、`$04`、`$08` 和 `$80`，以及 `$0a` |
| [`lut.py`](lut.py) | `KERNELS`, `expand(table, count)`, `blob(count)`, `cost(count)`, `image_bytes(count)` | 在整個輸入範圍上插值的四個表格，以及它們的大小 |
| | `plan(census, command)`, `planned(census)`, `table(runs, command, carrier)`, `encode(table)` | 每個指令一個表格，以範圍或已錄製的集合為索引，以及其編碼 |
| [`layout.py`](layout.py) | `runs(rom, least=256)`, `free(rom)`, `largest(rom)`, `fits(rom, wanted)`, `spread(rom, wanted)`, `must_grow(rom, wanted)` | 以 `(start, end)` 表示的 `$FF` 或 `$00` 連續區段、其總和、最長的一段，以及某大小能否放下 |
| [`patch.py`](patch.py) | `plan(rom, limit)`, `applied`, `spanned`, `hooked`, `rearmed`, `held`, `hooked_nmi`, `redirected`, `declared`, `checksummed`, `symbols(path)` | 指令執行的每個步驟，按此順序。`held` 在 `$07E84` 處所需的六個位元組不是空的時引發 `ArmGapTaken`，`hooked_nmi` 在中斷向量不指向 `$F0A0` 時引發 `VectorMoved` |

```python
import layout

image = bytes([0x42]) * 1_000 + bytes([0xFF]) * 600 + bytes([0x42]) * 10 + bytes(300)
print(layout.runs(image))
print(layout.free(image), layout.largest(image))
print(layout.fits(image, 500), layout.fits(image, 700), layout.must_grow(image, 1_000))
```

```
((1000, 1600), (1610, 1910))
900 600
True False True
```

## 狀態

每個有傳回值的指令，在三份錄製記錄所含的每個問題上，答案都與晶片的答案完全相同。剩下的是速度，記錄在 [`OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md) 中。

| 部分 | 狀態 |
|:--|:--|
| 傾印檔識別，全部三個地區 | 按 SHA-256 與 [`artifacts.manifest.json`](artifacts.manifest.json) 對照 |
| 每個卡帶在哪裏存取晶片 | 兩種存取格式，均已與錄製記錄對照 |
| 卡帶可以發出哪些指令 | 每個映像檔 20 個，已與錄製記錄對照 |
| 晶片給出甚麼答案 | 執行它本身的微碼 |
| 錄製記錄所含的參數組 | 三次執行共 73,341 個 |
| 晶片計算所用的表格 | 四個，1,280 位元組，完全重建 |
| 沒有公式能重現的三個表格 | 從晶片取得，294,912 位元組 |
| `$02` 的狀態，即 `$0a` 讀取的全部內容 | 三個從晶片取得的表格，59,686 位元組，在全部 6,980 個參數組中沒有任何鍵帶兩個答案 |
| `$00`、`$08` 和 `$04` | 65816 算術，各在 400 個隨機參數組上與晶片完全一致 |
| 已錄製答案的表格 | 12 個指令 |
| `$13` 和 `$18` | 在整個定義域上完整，從晶片驅動得出 |
| 查表 | 在每個已錄製的問題上完全正確，全部三個地區 |
| 後備 | 回答每個指令，包括沒有錄製記錄的鍵，不會陷入迴圈 |
| `$0a` | 65816，完全正確：在全部三份錄製記錄的 60 個參數組上，43,440 個答案字中 43,440 個正確 |
| 經重新導向窗口的存取 | 200 個三位元組存取各自換成三位元組呼叫，另有五個連續區段整段替換 |
| 用讀取值進行計算的長存取 | 七個已重新導向，六個 `adc` 和一個 `eor` |
| 遊戲本身經窗口所在記憶庫進行的工作 RAM 讀寫 | 全部 31 個已重新導向。[`OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md) 第 30 節 |
| 示範 | 能飛行、繪出地面，並在遊戲幀 405（比較執行的結尾）之前一直跟隨零售版卡帶的飛行。工作 RAM 每幀相差 30 至 60 位元組，其中 22 個在每一幀都不同，而其中十二個是遊戲複製到工作 RAM 的已修補呼叫 |
| 儀表板 | 在每個畫面上都有繪出。整個示範的螢幕亮度分佈範圍為 0.05，處於零售版卡帶的水平。第 32 節 |
| 橫切儀表板的帶狀條紋 | 出現在 2.2% 的幀上。第 48 節 |
| `$02` 留下的十個字 | 計算得出或從涵蓋整個鍵的表格讀取，在橫跨示範的 596 幀上十個全部與晶片完全一致 |
| 映像檔大小 | 會擴大，但在低速卡帶可定址的範圍內 |

### 速度

| 量度項目 | 數值 |
|:--|:--|
| 一次 `$0a` 呼叫，示範中 149 幀的平均值 | 77,044 個處理器週期 |
| 一次非首次的 `$0a` 呼叫 | 130,147 個週期，在一次飛行的 24 個狀態中穩定在 3% 以內 |
| 距離與上一行相同、因而複製答案的行 | 63.6% |
| 每行六次表格乘法，佔 `$0a` 的比例 | 54.7% |
| 建立四個乘法表格，在任何幀之外 | 62,665 個週期 |
| 從錄製記錄查找 600 個鍵一次 | 1,566,405 個週期 |
| 讀取一次耗費 8 個主時鐘時的一幀 | 44,671 個處理器週期 |
| 晶片，每次呼叫遊戲被阻塞的實際時間 | 數十個至約 250 個週期，中位數幀為 43 次呼叫，約 2,700 個 |
| `$00`、`$08` 和 `$04` 的算術 | 398、920 和 833 個週期 |

以上在處理器模型上量度，從未在主機上量度。一項改動會移動量度窗口開啟時示範所處的位置，因此主機的幀率計數器與工作量並非單調關係：在地面處理中加入 25,566 個週期的無用工作，反而令它報告更好的幀率。第 36 至 39、49、51 和 52 節記錄了這些執行。

在整個遊戲幀中，按程式計數器取樣並與組譯器的行對照表比對：

| 位置 | 佔比 |
|:--|--:|
| 地面 | 46.8% |
| 已錄製答案的搜尋 | 20.6% |
| 遊戲本身的程式碼 | 15.4% |
| 埠 | 11.2% |

兩個不需要搜尋的指令由 [`lutbuild.py`](lutbuild.py) 輸出為計算行號的程式碼。其中一個每遊戲幀被問 9.4 次。第 50 節。

### 表格涵蓋遊戲的多少

用部分錄製記錄建立，再用其餘部分提問：

| 提問內容 | 命中率 |
|:--|--:|
| 建立時所用的問題 | 100% |
| 同一吸引模式示範的另一份錄製記錄 | 93.4% |
| 一份錄製記錄的後半，而表格學習了其前半 | 11.2% |

三份錄製記錄都是同一個吸引模式序列，因此中間的數字量度的是重複程度。最後一個數字是玩家做了示範中從未做過的事時會遇到的情況。在該數字中，`$10` 命中 10.9%，`$06` 為 0%。`$06` 佔遊戲所有呼叫的 31.7%。

`$13` 和 `$18` 不以這種方式量度，因為它們不會落空。它們的參數是量化的：`$13` 的其中一個字跨度為 32,769，卻只取七個值，因此按跨度計算為 5.48e17 行，按值計算則為 1,512 行。每種組合都已從晶片驅動得出，而錄製記錄所含的全部 248 行在以同樣方式驅動時都得出相同結果。

`$10` 的定義域有 4,996 種組合，沒有補全。只以其鍵驅動時，它在 100 次中有 83 次重現錄製記錄，因此填入的行會有 17% 是錯的。缺少的行會退回程式碼處理，錯誤的行則不會。

### 查表給出的答案

在處理器模型上對照三份錄製記錄驅動，每個地區每個指令四十個問題：

| 指令 | 正確 | 錯誤 |
|:--|--:|--:|
| `$00` `$02` `$03` `$06` `$08` `$0c` `$0d` `$0e` `$10` `$13` `$14` `$1b` `$28` | 各 120 | 0 |
| `$04` | 40 | 0 |
| `$18` | 10 | 0 |

錄製記錄中 `$04` 和 `$18` 的不同問題較少。

## 量度了甚麼

### 一個替代方案涵蓋全部三個地區

在程式碼中讀取對數據埠的儲存指令，涵蓋卡帶使用的兩種格式，USA 映像檔中有 208 個，日本版有 218 個，歐洲版有 208 個。從中讀出的二十個指令位元組在三者中都是同樣的二十個。

長格式在每個地區都落在兩個位址：`$3f:8000` 有 84 條指令，`$3f:c000` 有 9 條，三者的數目相同。這是同一個驅動程式出現三次，因此一個地區的替代方案也是另外兩個地區的替代方案。

### 搜尋長格式時看不到驅動程式的大部分

熱點路徑以 `pea $003f` 和 `plb` 設定一次數據記憶庫，然後使用只寫兩個位元組、不指明記憶庫的絕對儲存指令。以日本版映像檔的錄製記錄量度，該記錄帶有每次存取的程式計數器：

| | 指令 | 長格式 | 絕對格式 | 長格式傳送的位元組佔比 |
|:--|--:|--:|--:|--:|
| 寫入晶片 | 118 | 40 | 78 | 62.2% |
| 從晶片讀取 | 47 | 13 | 34 | 7.9% |

[`commands.py`](commands.py) 兩種都會讀取。遊戲中最熱的迴圈是 `plb` 之後的 `sta $8000`，隨後是 176 次輪詢並讀取。

按編碼搜尋也會報告不是指令的位元組。在 USA 映像檔中，122 個長格式匹配中有 29 個位於記憶庫 `$30` 至 `$3e` 中 29 個不同的位址，每處一個。日本版有 28 個，歐洲版有 30 個，三個總數之間的差異全部來自這些匹配。

### 每個指令讀取多少個字

透過晶片的協定量度：寫入的字比指令所需少一個時，指令仍會回應；多寫一個時則沒有回應。計數就是從該沉默處退後一個。這已用算術核對：指令 `$00` 回答其兩個字以十五個小數位元計算的有號乘積，`0x1234 x 0x5678 -> 0x0C4C`。

256 個指令位元組中有四十五個會作答。

| 輸入字數 | 輸出字數 | 指令數 | 存放全部答案的表格 |
|--:|--:|--:|:--|
| 1 | 1 | 2 | 131,072 位元組，放得下 |
| 2 | 1 | 2 | 8,589,934,592 位元組，是 96 Mbit 映像檔的 683 倍 |
| 3 | 1 | 14 | 562 TB |
| 4 | 1 | 7 | 更大 |
| 5 | 1 | 17 | 更大 |
| 6 | 12 | 1 | 更大 |
| 10 | 1 | 2 | 更大 |

有兩個指令可以儲存全部答案。其餘四十三個中最小的也是 96 Mbit 映像檔的 683 倍。上表計算的是晶片輸入定義域的大小。遊戲所問的遠少於此，以下各節計算其大小。

### 遊戲問甚麼

日本版映像檔在沒有輸入的情況下執行 12,000 幀，讓吸引模式示範飛行，期間從 30 個發出點發出了 257,189 個指令。NTSC 映像檔在第 10,418 幀後不再存取晶片，而 PAL 版在 11,999 幀時仍在飛行，這就是歐洲版會發出 `$04` 而另外兩個從不發出的原因。

| 指令 | 佔比 | 發出次數 | 發出點 | 內容 |
|:--|--:|--:|--:|:--|
| `$06` | 28.9% | 74,261 | 2 | |
| `$13` | 25.4% | 65,332 | 1 | |
| `$00` | 15.0% | 38,668 | 10 | 有號乘法，即時計算 |
| `$11` | 4.7% | 12,136 | 2 | |
| `$0a` | 2.7% | 6,946 | 1 | 以一個被讀取 176 次的數據流作答 |
| 其餘 13 個 | 23.3% | 59,846 | 14 | |

### 在發出點切分錄製記錄

`$0a` 以一個被卡帶讀取 176 次的數據流作答，而晶片在該數據流期間接受寫入。於是一次交換內的讀取看起來像是交換的結束，照此切分的話，十分之一的區段會包含來自相距超過 32 位元組的程式碼的寫入。

[`exchanges.py`](exchanges.py) 改為在指令發出點切分。只觸及數據埠低半部的程式計數器發出了一個指令，而觸及兩個半部的則寫入了參數字。

全部三次執行合計：19 個指令共 73,341 個不同參數組，每個儲存一個答案時為 586,728 位元組。

| | 指令 | 行 | 位元組 | 流量佔比 |
|:--|--:|--:|--:|--:|
| 內嵌比較鏈 | 5 | 22 | 176 | 30.5% |
| 表格 | 13 | 46,832 | 374,656 | 54.3% |
| 即時計算，因為是乘法 | 1 | 無 | 0 | 15.8% |

### 晶片計算所用的資料

uPD77C25 在程式旁邊保存 1024 個字的數據 ROM。[`tables.py`](tables.py) 按公式重建每個候選表格並搜尋它。其中四個存在，逐字相符：

| 表格 | 字數 | 公式 | 位元組 |
|:--|--:|:--|--:|
| 倒數 | 128 | `2^22 / (128 + k)`，四捨五入並鉗位 | 256 |
| 正弦 | 128 | `sin(pi k / 128) x 32768`，捨去小數 | 256 |
| 餘弦 | 128 | `cos(pi k / 128) x 32768`，捨去小數 | 256 |
| 反餘弦 | 256 | `acos(k / 256) x 32768 / pi` | 512 |
| | | **總計** | **1,280** |

沒有平方根，也沒有反正切。兩個掩膜版本都帶有同樣的四個表格，DSP-1B 把其中三個放在低兩個字的位置。

### 每個參數的取值範圍

[`exchanges.py`](exchanges.py) 報告每個參數位置的最低值、最高值和不同值的數目：

| 參數位置的情況 | 指令數 | 表格的索引依據 |
|:--|--:|:--|
| 一個或少數幾個值 | 5 | 這些值，內嵌 |
| 幾千個，填滿其範圍 | 2 | 範圍，2^18 和 2^20 行 |
| 至少一個跨越整個字 | 12 | 沒有稠密的依據 |

指令 `$0d` 在三個位置中每個都取大約四千個不同值，而每個都跨越完整的 0 至 65,535。以範圍建表會有 2^48 行，幾乎全都是沒有人會傳送的輸入，因此兩個數字總是一併報告。

### 晶片保存狀態

十六個會作答的指令中，有七個對相同的參數給出不同的答案，因為讀取另一個指令所載入矩陣的指令，並不是其自身參數的函數。`$0e` 在每份錄製記錄中只取一個參數組，卻以 6,260 種不同方式作答。

當鍵還包含一個較早指令的參數時，七個中有六個會變得確定，這就是 [`lutbuild.py`](lutbuild.py) 中的 `CARRIER`：

| 指令 | 以其參數及最近一次的以下指令為鍵 |
|:--|:--|
| `$03` | `$14` |
| `$06`、`$0d`、`$0e` | `$02` |
| `$13`、`$1b` | `$11` |

`$0a` 是第七個。沒有任何較早的指令能確定它，無論單獨一個，還是任何兩個或三個的組合。儲存每個不同的完整答案需要 16,762,160 位元組，而儲存四字步進則在任何索引之前已有 538,583 個不同步進。因此改為即時計算：每行一次正規化、一次倒數、兩次乘法和兩次移位，逐個階段從晶片的程式中讀出，並與其暫存器核對。第 22 節。

### 表格編碼後的大小

[`lutbuild.py`](lutbuild.py) 按鍵為每個指令的行排序，讓卡帶以二分法找到某一行。來自三份錄製記錄，在補全 `$13` 和 `$18` 之前：

| 指令 | 鍵 | 行 | 鍵字數 | 答案字數 | 位元組 |
|:--|:--|--:|--:|--:|--:|
| `$06` | 參數及最近的 `$02` | 75,278 | 10 | 3 | 1,957,228 |
| `$0d` | 參數及最近的 `$02` | 6,557 | 10 | 3 | 170,482 |
| `$02` | 參數 | 6,980 | 7 | 4 | 153,560 |
| `$0e` | 參數及最近的 `$02` | 6,980 | 9 | 2 | 153,560 |
| `$03` | 參數及最近的 `$14` | 5,268 | 9 | 3 | 126,432 |
| `$14` | 參數 | 4,406 | 6 | 3 | 79,308 |
| `$28` | 參數 | 6,182 | 3 | 1 | 49,456 |
| `$1b` | 參數及最近的 `$11` | 2,986 | 7 | 1 | 47,776 |
| `$0c` | 參數 | 3,480 | 3 | 2 | 34,800 |
| `$10` | 參數 | 2,498 | 2 | 2 | 19,984 |
| `$13` | 參數及最近的 `$11` | 244 | 7 | 3 | 4,880 |
| `$18` | 參數 | 4 | 4 | 1 | 40 |
| | | | | **總計** | **2,797,956** |

即 86 個 32,768 位元組的記憶庫。一行除了答案還帶有其鍵，而 `$06` 用十個字的鍵換取三個字的答案，因為晶片保存狀態。

### 錄製記錄能說明與不能說明的事

錄製記錄說明遊戲做了甚麼，永遠不能說明它能做甚麼。大部分參數來自飛機的姿態，幾乎每一幀都取新值，因此沒有錄製記錄能顯示其輸入集合已經封閉。所以每個指令在表格後面都有程式碼實現的後備。

閱讀程式碼回答了另一半。[`commands.py`](commands.py) 從每個映像檔中讀出 20 個指令位元組，歐洲版多讀出一個 `$80`。與日本版錄製記錄對照，在執行過的 30 個發出點中有 27 個一致，沒有矛盾，三個無法判斷。與歐洲版對照，36 個中有 33 個一致，沒有矛盾。

| | 指令 |
|:--|--:|
| 從程式碼讀出，全部三個映像檔 | 20 |
| 歐洲版另外讀出 | `$80` |
| 日本版錄製記錄發出的 | 18 |
| 歐洲版錄製記錄發出的 | 19 |
| 讀出但從未見到執行的 | `$21`、`$23` |

`$80` 令晶片回到等待指令的狀態。卡帶在 `$0702a` 處連續寫入它 128 次以清空晶片。

### 零售版映像檔中的空間

[`layout.py`](layout.py) 量度長度為 256 位元組或以上、由同一位元組重複組成的連續區段：

| 地區 | 這些區段中的空閒空間 | 最大的單一區段 |
|:--|--:|--:|
| USA | 63,122 | 4,249 |
| 日本 | 74,207 | 8,395 |
| 歐洲 | 63,122 | 4,249 |

每個都能完整容納四個合共 1,280 位元組的表格。已錄製答案的表格放不下，因此映像檔會擴大。由同一位元組重複組成的連續區段是沒有東西使用它的證據，所以在放入任何東西之前，候選區段都會與驅動程式普查對照。

<a id="the-dumps"></a>

## 傾印檔

按 No-Intro 的命名方式命名。每個摘要都是對整個檔案、不含複製機標頭計算的。以 SHA-256 為準，CRC32 則用於與仍以它為鍵的資料庫交叉核對。

| 檔案 | 讀取路徑 | 大小 |
|:--|:--|--:|
| Pilotwings，USA | `external/roms/pilotwings-usa.sfc` | 524,288 |
| Pilotwings，日本 | `external/roms/pilotwings-jp.sfc` | 524,288 |
| Pilotwings，歐洲 | `external/roms/pilotwings-eur.sfc` | 524,288 |

| 地區 | SHA-256 | CRC32 |
|:--|:--|:--|
| USA | `03d0127f5de3237e22ad00de0c20763274da7b71142dde693240ac96d10983a3` | `266C44ED` |
| 日本 | `d1845de22c3c7f2606bda20e09c8f7a78f92f5cbbb6bfe01f96a1d1e84b30394` | `77871727` |
| 歐洲 | `f70a72f3d3a65497cdc4d849877a29cf4f7bd10439bb7f5cb8675cdfc0e706d4` | `DEF45776` |

三個都聲明版本為 `0x00`。以本遊戲為基礎製作的 Nintendo Campus Challenge 卡帶同樣是 524,288 位元組，聲明同樣的晶片組 `0x03`，並帶有同樣的內部標題 `PILOTWINGS`。只有它的映射位元組和摘要能把它區分出來，這就是只以摘要識別的原因。

## 底層模型

| 模型 | 子模組 | 對照依據 |
|:--|:--|:--|
| 65816 | [mos65xx-python](https://github.com/gufranco/mos65xx-python) | 逐個操作碼的測試套件，5,120,000 個案例 |
| DSP-1 | [snes-dsp-python](https://github.com/gufranco/snes-dsp-python) | 執行晶片本身的微碼 |
| 卡帶映射 | [snes-mapper-python](https://github.com/gufranco/snes-mapper-python) | 一個真實卡帶庫中的每種標頭組合 |
| ROM 映像檔 | [snes-rom-image-python](https://github.com/gufranco/snes-rom-image-python) | 同一個庫，經重寫後核對 |
| 驅動程式 | [snes-driver-python](https://github.com/gufranco/snes-driver-python) | 卡帶程式碼在哪裏存取其協處理器 |

沒有圖形模型。這顆晶片只計算數字，從不觸及圖塊。

上面每個週期數都來自 65816 模型這個儀器：它逐個週期驅動匯流排，所以一個常式的耗費就是它實際用掉的週期。它啟動時記憶體和暫存器存放可重現的打亂值而不是零，因此讀取從未寫入的內容會顯示為錯誤答案。

## 一切在卡帶中的位置

低速卡帶帶有記憶庫 `$00` 至 `$7D`。本專案加入的一切都經 `$80` 及以上的鏡像讀取，一旦設定 `$420D`，該鏡像以六個主時鐘而非八個回應一次讀取。

| 內容 | 記憶庫 | 讀取經由 |
|:--|:--|:--|
| 出廠時的遊戲 | `$00`-`$0F` | |
| 替代方案的程式碼 | `$10` | `$90` |
| 從晶片取得的正弦和餘弦 | `$11`-`$18` | `$91`-`$98` |
| 已錄製的答案 | `$19`-`$6F` | `$99`-`$EF` |
| `$02` 的狀態，供 `$0a` 讀取 | `$70`-`$72` | `$F0`-`$F2` |
| 從晶片取得的倒數 | `$73` | `$F3` |
| 遊戲經重新導向的存取所落入的窗口 | `$7D` | `$7D` |

回答全部十二個已錄製的指令需要 87 個記憶庫，其中 60 個用於 `$06`。只要能換來準確度、穩定性或速度，映像檔可以擴大到 96 Mbit。`$7D` 以上的每個記憶庫都需要窗口式佈局，因此映像檔在可能的情況下保持在其以下。一旦標頭的大小位元組相符，2 MiB 和 4 MiB 的映像檔都能開機並以相同方式執行示範，而 [`patch.py`](patch.py) 會按映像檔的長度設定該位元組。

## 結果正確嗎

有兩個準則，這裏沒有任何東西自行計算 DSP-1 的結果。零售版卡帶決定問甚麼：一個指令和一個參數組之所以是一個問題，是因為零售版卡帶會傳送它們。晶片的微碼決定答案，透過 [snes-dsp-python](https://github.com/gufranco/snes-dsp-python) 執行。

| 主張 | 對照依據 | 位置 |
|:--|:--|:--|
| 傾印檔就是該傾印檔 | [`artifacts.manifest.json`](artifacts.manifest.json) 中的 SHA-256 | [`tools/identify.py`](tools/identify.py) |
| 卡帶在哪裏存取晶片 | 對程式碼的解讀與一次執行的錄製記錄雙向核對 | [`commands.retail.test.py`](commands.retail.test.py)、[`sites.retail.test.py`](sites.retail.test.py) |
| 常式給出甚麼答案 | 向晶片提出同一問題 | [`routines.retail.test.py`](routines.retail.test.py)、[`raster.retail.test.py`](raster.retail.test.py)、[`attitude.retail.test.py`](attitude.retail.test.py) |
| 四個表格 | 微碼的數據 ROM，逐字相符 | [`tables.retail.test.py`](tables.retail.test.py) |
| 修補 | 零售版映像檔 | [`patch.retail.test.py`](patch.retail.test.py) |

需要傾印檔或微碼的檢查放在十個 `*.retail.test.py` 檔案中，共 96 個測試，任一缺少時會報告自己被略過。在兩者都有的機器上，關卡檢查會像其他檔案一樣按 100% 量度它們。CI 無法持有其中任何一項，因此以 `RETAIL_INPUTS=absent` 執行，覆蓋率報告不包括它們。

本專案重現 DSP-1，從不重現 DSP-1B。吸引模式示範是按鍵輸入的錄製，而在 DSP-1B 經修正的算術下，飛機以同樣的輸入會撞向地面。零售版電路板帶的是哪個掩膜版本，無法從傾印檔中讀出。這個問題，以及所有範圍比表面看來更窄的主張，都記錄在 [`OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md) 中，每項都附有能確定答案的量度方法。

## 參與開發

| 需要 | 位置 |
|:--|:--|
| 每個關卡檢查及其執行順序 | [CONTRIBUTING.md](CONTRIBUTING.md) |
| 給編程代理的同一內容 | [AGENTS.md](AGENTS.md) |
| 本儲存庫與同系列其他儲存庫共用的標準 | [FAMILY.md](FAMILY.md) |
| 錯誤報告 | [GitHub Issues](https://github.com/gufranco/snes-pilotwings-nochip/issues) |
| 安全報告 | [SECURITY.md](SECURITY.md) |

```bash
./run.sh --gates
```

44 個檔案共 1,093 個測試，每個模組旁邊有一個 `<module>.test.py`。覆蓋率是硬性關卡，陳述式和分支須達 100%，在 [`pyproject.toml`](pyproject.toml) 中設定。提交遵循 Conventional Commits，semantic-release 據此決定版本。

註解只出現在組合語言中：入口和出口狀態、暫存器寬度，以及每個位址的來源。Python 原始碼不帶任何註解。

切勿把卡帶或微碼映像檔附加到 issue，也切勿連結到可以下載其中任何一個的地方。摘要可以識別檔案而不帶有檔案本身。

## 參考資料

- No-Intro，提供三個零售版傾印檔的名稱和摘要。
- 位於 commit `2971061cf07fdc6fc7d18883edf4e648eb16a6d2` 的 snes9x，https://github.com/snes9xgit/snes9x ，由 [`Dockerfile`](Dockerfile) 建置，用於錄製每次埠存取。錄製記錄是關於該模擬器的 DSP-1 的證據，這就是查表要與晶片本身的微碼而不是與錄製記錄對照的原因。
- asar v1.81，https://github.com/RPGHacker/asar ，由 [`Dockerfile`](Dockerfile) 建置。
- neviksti 的無晶片 Star Ocean 轉換，提供大於低速卡帶定址空間的映像檔的定址規則。
- Nintendo EAD 和 Argonaut，製作了這個遊戲。

## 引用本專案

[CITATION.cff](CITATION.cff) 在每次發行時由 [`scripts/set-version.sh`](scripts/set-version.sh) 更新，該腳本同時為 [`version.py`](version.py) 加上版本標記。

## 授權

MIT。見 [LICENSE](LICENSE)。授權涵蓋工具、組合語言程式碼和本文件，但不授予遊戲的任何權利。這裏不發佈任何 ROM 數據：一切都在你自行提供的傾印檔上運作。
