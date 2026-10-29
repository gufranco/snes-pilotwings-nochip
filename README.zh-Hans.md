# 没有 DSP-1 的 Pilotwings

一套工具，为全部三个地区版本构建 Pilotwings 镜像，其中 DSP-1 协处理器被卡带内的表和 65816 代码取代。游戏提出什么问题以零售版卡带为准，每个答案以芯片自身的微码为准。

[English](README.md) | [日本語](README.ja.md) | 简体中文 | [繁體中文（香港）](README.zh-HK.md)

[![CI](https://github.com/gufranco/snes-pilotwings-nochip/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/snes-pilotwings-nochip/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**16** 条命令对照芯片回答了 **3** 份地区录制所含的每个问题，**0** 个错误答案，`$0a` 地面字 **43,440** 个中 **43,440** 个完全一致，**1,093** 个测试，每个模块的语句和分支覆盖率均为 **100%**，除标准库外没有依赖，另有 **5** 个固定版本的子模块

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

第一个循环根据公式重建 DSP-1 存放在其数据 ROM 中的四张表，[`tables.py`](tables.py) 正是在微码中搜索这些表。第二个循环计算一张表的大小，该表保存某条命令的全部答案，命令读取一个、两个或三个参数字：一个字能放进 96 Mbit 卡带，两个字放不下。这一行说明了为什么替代方案只存储游戏会问到的答案，其余的靠计算。

## 安装

### 分步操作

从零到可用的检出共五步。第 4 步的 doctor 会确认前三步。

1. **只安装 git 和 Docker。** Python 以及构建用到的每个工具都在本项目的 Docker 镜像里，第一条命令会构建它。

   | | Windows | macOS | Linux |
   |:--|:--|:--|:--|
   | git | `winget install Git.Git` | `xcode-select --install` | 发行版的 `git` 软件包 |
   | Docker | `winget install Docker.DockerDesktop`，然后启动 Docker Desktop | Docker Desktop，或 `brew install colima docker` 后运行 `colima start` | Docker Engine，然后 `sudo systemctl start docker` |

   在 Windows 上，本页写 `./run.sh` 的地方请输入 `.\run.cmd`。

2. **克隆仓库，不要下载。**

   ```bash
   git clone --recurse-submodules https://github.com/gufranco/snes-pilotwings-nochip.git
   cd snes-pilotwings-nochip
   ```

   > [!CAUTION]
   > 只有克隆才能得到可用的副本。GitHub 上绿色的 **Code** 按钮还提供 **Download ZIP**，但 ZIP 在这里永远无法使用：本项目依赖的 5 个模型是以 git 子模块固定的独立仓库，ZIP 一个都不包含，之后也无法补上。启动脚本会拒绝这样的副本并说明原因；请删除它并克隆。没有加 `--recurse-submodules` 的克隆，可以用 `git submodule update --init --recursive` 就地修复。

3. **把转储放进 `external/roms/`**，文件名按[转储列表](#the-dumps)：`pilotwings-usa.sfc`, `pilotwings-jp.sfc`, `pilotwings-eur.sfc`。微码放在 `external/firmware/`。然后检查，你提供的每个转储都应显示 `ok`。这第一条命令会构建镜像，需要几分钟；之后的命令会立即开始：

   ```bash
   ./run.sh tools/identify.py
   ```

4. **运行 doctor。** 它检查检出、每个模型、每个转储和镜像中的工具，最后说明下一步运行什么：

   ```bash
   ./run.sh doctor.py
   ```

   ```
     N checks, nothing to report
     next: ./run.sh tools/identify.py, or on Windows .\run.cmd tools/identify.py
   ```

   标有 `!` 的行，下一行写着该怎么做。doctor 和启动脚本能发现的设置错误：

   | 提示 | 怎么做 |
   |:--|:--|
   | `This folder has no git metadata` | 删除文件夹并克隆，第 2 步 |
   | `Docker is not installed` | 第 1 步 |
   | `Docker is installed but its engine is not answering` | 启动 Docker Desktop，或 `sudo systemctl start docker` |
   | `... is not checked out` | `git submodule update --init --recursive` |
   | `cartridge ...: missing` | 第 3 步 |

5. **目前还没有单一的构建命令。** 本项目高度实验性：它通过“接口”中的命令录制游戏、构建表并给镜像打补丁，预计会有很多问题。欢迎报告。

### 依赖与 doctor

| 要求 | 版本 |
|:--|:--|
| git | 任意版本，用于获取五个子模块 |
| 你自己的卡带转储 | 每个 524,288 字节，放在 `external/roms/` 中，文件名见[转储](#the-dumps) |
| 你自己的 DSP-1 微码副本 | 8,192 字节，存为 `external/firmware/dsp1.bin` 和 `external/firmware/dsp1b.bin` |
| Docker | 任意当前版本，且正在运行。Python 3.12、asar 1.81 和录制用模拟器都在 [`Dockerfile`](Dockerfile) 描述的镜像中，[`run.sh`](run.sh) 在其中运行每条命令 |

除 Docker 和 git 外，不在你的机器上安装任何东西，运行时也不下载任何东西。本项目用来衡量自身的五个模型是仓库根目录下的 git 子模块。通过下载 zip 链接得到的源码归档不包含其中任何一个，诊断脚本会把这样的文件夹报告为归档。

微码可以放在 `UPD7725_FIRMWARE_DIR` 指定的任意位置，而不是 `external/firmware/`。没有微码时，所有驱动芯片的检查都会报告没有可运行的内容。

诊断脚本会打印机器信息、本项目的版本、该文件夹是否为 git 克隆、每个模型及其版本、微码能否运行、两个掩模版本中有哪些、每份转储的状态，以及每个模型自身诊断脚本的报告，按该模型的名称归档。所有检查都通过时退出码为 0，否则为 1。提交任何 bug 报告时请粘贴它的完整输出。在一次全新的递归克隆上，没有转储也没有微码时，它的结尾是：

```
  5 of 95 checks did not pass
  next: fix the first line marked ! above, then run ./run.sh doctor.py, or on Windows .\run.cmd doctor.py
```

这五项是：缺失的微码、DSP 模型没有镜像的两个掩模版本，以及两个子模块各自附带的空 `cartridges` 目录。

## 接口

这是一组从仓库根目录运行的脚本，以及构成它们的模块。需要参数的脚本在缺少参数时会打印用法行并以 2 退出。

### 命令

| 命令 | 参数 | 作用 | 退出码 |
|:--|:--|:--|:--|
| `./run.sh doctor.py` | 无 | 报告机器信息和整条模型链 | 0 表示正常，1 表示有检查未通过 |
| `./run.sh tools/identify.py` | 无 | 将 `external/roms/` 中的每个文件与 [`artifacts.manifest.json`](artifacts.manifest.json) 对照检查，并打印在 macOS、Linux 和 Windows 上计算 SHA-256 的命令 | 0 表示每份转储都匹配或不存在，1 表示有一份不对 |
| `./run.sh exchanges.py <trace>` | 一份录制 | 在每个命令调用点切分录制，打印每条命令及其交换、占比、不同参数组、调用点以及可以如何作答 | 0、2 |
| `./run.sh tables.py <microcode image>` | 一个 8,192 字节的镜像 | 在镜像的数据 ROM 中找到四张表，并打印每张表起始的字 | 0、2 |
| `./run.sh microcode.py <mask>` | `dsp1` 或 `dsp1b` | 遍历微码对全部 256 个命令字节的分派，打印每个处理程序以及卡带写入的命令 | 0、2 |
| `./run.sh layout.py <image> <bytes wanted>` | 一个镜像和一个大小 | 查找 256 字节或更长的 `$FF` 或 `$00` 连续段，并说明镜像能否在不扩容的情况下容纳该大小 | 0、2 |
| `./run.sh lut.py [<rows>]` | 每张表的行数，默认 65,536 | 计算在整个输入上制表后四张表的大小 | 0 |
| `./run.sh derived.py <mask> [<directory>] [--reindex]` | 一个掩模版本，输出目录，默认 `build` | 驱动芯片计算 `$4000` 到 `$7FFF` 上的倒数以及 65,536 个角度上的正弦和余弦，并对每个字统计前导倍增次数。把 `reciprocal`、`recip-up`、`recip-down`、`recip-exponent`、`leading`、`sine` 和 `cosine` 写成 32,768 字节的分片，命名为 `<stem>-<n>.bin`。`--reindex` 根据磁盘上已有的倒数重建三张 `recip-` 表 | 0、2 |
| `./run.sh state02build.py <mask> [<directory>]` | 一个掩模版本，存放录制并接收输出的目录，默认 `build` | 对录制中的每个参数组驱动 `$02`，写出它的三张状态表 `state02-map.asm`、`state02-data.asm`，以及 65,536 个角度上经过钳位的余弦 | 0、2 |
| `./run.sh lutbuild.py <mask> [<directory>]` | 一个掩模版本，输出目录，默认 `build` | 根据 `build/trace-usa.bin`、`build/trace-jp.bin` 和 `build/trace-eur.bin` 构建已录制答案表，通过驱动 DSP-1 补全 `$13` 和 `$18`，并写出 `lut-<n>.bin`、`lut-map.asm` 和 `lut-axes.asm` | 0、2 |
| `./run.sh patch.py <rom> <symbols> <out> <game bytes> [--slow]` | 汇编后的镜像，由 `name hex` 行组成的符号文件，输出路径，镜像内游戏部分的长度 | 把卡带对芯片的每次访问指向替代实现，从文件头中清除协处理器，设置大小字节，除非给出 `--slow` 否则设置快速 ROM 位，并重写校验和 | 0，1 表示镜像没有访问芯片，2 |
| `./run.sh tools/cycles.py <image> <assembler log> [<routine>] [<snapshot>]` | 一个镜像，汇编器打印的符号，默认例程 `ground_block`，默认快照 `build/nb2/wram-000300.bin` | 在 65816 模型上运行该例程一次，打印其周期数和指令数 | 0，1 表示没有快照，2 |
| `./run.sh tools/profile.py <image> <symbol file> [<routine>] [<snapshot>] [--built]` | 同上，快照中已包含构建好的表时加上 `--built` | 运行一次调用，按每条指令所在的标签拆分其周期数，列出前 16 个 | 0，1 表示没有快照或标签，2 |

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

对 `external/firmware/dsp1b.bin` 运行同一命令时，找到的正弦、余弦和反余弦低两个字，分别位于 278、406 和 540，倒数位于 101。

### 录制用模拟器

镜像中的 `pwemu` 由 [`emu/`](emu/) 构建，即 commit `2971061cf07fdc6fc7d18883edf4e648eb16a6d2` 处的 snes9x，在每次 DSP-1 端口访问上加了钩子，外面套一个最小的 libretro 前端。

```bash
./run.sh --exec env PWTRACE=build/trace-usa.bin pwemu external/roms/pilotwings-usa.sfc 12000
```

| 输入 | 含义 |
|:--|:--|
| `<rom> <frames>` | 镜像和要运行的帧数 |
| `PWTRACE` | 二进制端口日志的路径 |
| `PWSCRIPT` | 输入脚本，每行一条 `frame button...`，按键名为 `up`、`down`、`left`、`right`、`a`、`b`、`x`、`y`、`l`、`r`、`start` 和 `select` |
| `PWRAM` | 接收所有没有任何一帧改动过的工作 RAM 连续段的路径，格式为 `start end length` |
| `PWPC` | 接收每帧采样一次的程序计数器的路径 |

它以 `RESULT load=ok frames=<n> delivered=<n> accesses=<n> brightness=<x>` 结尾并以 0 退出，镜像无法读取或加载时以 1 退出。

端口日志中每条记录为 12 字节，小端序：32 位的帧号，32 位的带 bank 的程序计数器，16 位的端口地址，1 表示读、0 表示写，以及传送的字节。[`exchanges.py`](exchanges.py) 和 [`census.py`](census.py) 读取这种格式。

[`emu/native.cpp`](emu/native.cpp) 通过运行时加载的 libretro 核心完成同样的录制，用法为 `native <core> <rom> <frames>`；[`emu/play.cpp`](emu/play.cpp) 为某个核心打开一个窗口，用法为 `play <core> <rom>`。

### 汇编器

镜像中带有由 [`Dockerfile`](Dockerfile) 构建的 asar v1.81。[`asm/nochip.asm`](asm/nochip.asm) 是入口文件。它把替代实现放在 bank `$10`，包含 [`asm/`](asm/) 中所有其他 `.asm` 文件，并读取上述脚本写入 `build/` 的表。它打印的 `SYM <name> <address>` 行就是 [`tools/cycles.py`](tools/cycles.py) 读取的内容。

### 转储、版本以及底层模型

| 模块 | 调用 | 返回 |
|:--|:--|:--|
| [`dumps.py`](dumps.py) | `artifacts()` | 三条 `Artifact` 记录：`name`、`region`、`filename`、`declares`、`accepted`、`provenance` |
| | `identify(data, digest=None)` | SHA-256 匹配的 `Artifact`，或 `None` |
| | `identify_digest(digest)` | 同上，输入为已计算好的摘要 |
| | `diagnose(data, digest=None)` | 一个带有 `kind`、`detail` 和 `repair` 的 `Finding`。`kind` 为 `match`、`copier-header`、`wrong-size` 或 `unrecognised` |
| | `digest_commands(filename)` | `macOS`、`Linux` 和 `Windows` 上的 SHA-256 命令 |
| | `manifest()`、`through()`、`not_this()` | 清单、清单的来源，以及清单中列出的应拒绝的文件 |
| [`version.py`](version.py) | `VERSION`、`stamped(name, release=None)` | 发布版本，以及该版本镜像使用的文件名 |
| [`hardware.py`](hardware.py) | `install(environment=None)` | 把每个模型放到 `sys.path` 上，把 `external/firmware/` 加入 `UPD7725_FIRMWARE_DIR`，并返回该变量 |
| | `load(package)` | 一个模型包：`mos65xx`、`snesdsp`、`mapper`、`romimage`、`snesdriver` 或 `upd7725` |
| | `root_of(package)` | 模型所在目录。其他名称会抛出 `UnknownPackage` |
| [`tools/identify.py`](tools/identify.py) | `look(artifact, root)`、`judge(artifact, data)` | 一个 `Looked`，包含 `region`、`filename`、取值为 `ok`、`absent` 或 `wrong` 的 `state`、`detail` 以及 `ok` |

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

在这里，长度、芯片组或标题都不能用来识别转储，摘要总是能。

### 读取卡带的代码

| 模块 | 调用 | 返回 |
|:--|:--|:--|
| [`commands.py`](commands.py) | `accesses(rom)` | 对 `$8000` 处数据端口或 `$C000` 处状态端口的每个 `Access`，包括 bank `$3F` 中的长地址形式和绝对地址形式。每个都有 `offset`、`mnemonic`、`size`、`register`、`way` 和 `long` |
| | `stores(rom)`、`store_at(rom, at)` | 向数据端口存储的偏移，以及某个偏移处的存储 |
| | `read(rom, disassemble)` | 每个存储对应一个 `Site`，最多向前解码 512 字节，带有 `command`、`narrow`、`issues` 和 `why` |
| | `commands(sites)` | 这些调用点发出的命令字节，已排序 |
| [`sites.py`](sites.py) | `reached(rom)`、`census(rom)` | 长地址形式在哪里访问芯片，通过 [snes-driver-python](https://github.com/gufranco/snes-driver-python) 得出，以及一个包含 `sites` 和 `shapes` 的 `Census` |

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

### 读取录制

| 模块 | 调用 | 返回 |
|:--|:--|:--|
| [`exchanges.py`](exchanges.py) | `taken(trace)` | 每个 `Exchange`，在发出它的调用点处切分：`site`、`command`、`words`、`answer`，以及 `later`，即答案开始后写入的字 |
| | `issuing(trace)` | 只写数据端口低半部分的程序计数器，每个对应其唯一的命令字节 |
| | `census(trace)`、`read(path)` | 一个 `Census`，包含 `commands`、`total`、`issued(c)`、`distinct(c)`、`share(c)`、`sites(c)` 和 `table_bytes()` |
| | `spans(census, command)` | 每个参数位置一个 `Span`：`lowest`、`highest`、`distinct`、`width`、`bits`，不同值至少填满宽度一半时还有 `dense` |
| | `readings(runs, command)` | 一个 `Reading`，指出哪条更早的命令的参数能让键决定答案：`carrier`、`rows`、`ambiguous`、`pure`、`tabulatable` |
| | `tier_of(command, distinct)` | `$00` 为 `computed`，最多 16 个参数组为 `inline`，更多为 `table` |
| [`census.py`](census.py) | `taken(trace)`、`exchanges(trace)`、`report(census)` | 同样的问题，但在字节流上切分，每次读取都结束一个交换。`$0a` 会破坏这种切分。仅作为库使用：运行该文件不会打印任何内容 |

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

这段 trace 是录制格式中的三个 `$00` 交换。`$00A000` 处的调用点只向端口低半部分写一个字节，所以它是命令调用点，其后的两个字是参数。`$0C4C` 是 `$1234` 与 `$5678` 的有符号乘积，带十五个小数位，这正是芯片给出的答案。

### 询问芯片

这些模块通过 [snes-dsp-python](https://github.com/gufranco/snes-dsp-python) 驱动微码，因此每个都需要机器上有微码。

| 模块 | 调用 | 返回 |
|:--|:--|:--|
| [`tabulate.py`](tabulate.py) | `shape_of(command)`、`sweep(model="dsp1")` | 一个包含 `writes`、`reads` 和 `answers` 的 `Shape`，测量方法是每次多写一个字，直到芯片不再应答 |
| | `ask(command, words, reads=1)`、`deterministic(command=0)` | 答案字节，以及两个相同的问题是否得到相同的答案 |
| | `entries_for(words)`、`bytes_for(words, out=1)`、`storable(words)` | 覆盖整个输入的表的大小，以及它能否放进 96 Mbit 卡带的一半。这些不需要微码 |
| [`tables.py`](tables.py) | `KNOWN`、`carried(image)`、`find(words, table)`、`words(image)`、`table_bytes()` | 四条 `Table` 记录、每张表在镜像中的位置，以及它们的大小。对不是 8,192 字节的镜像，`words` 会抛出 `WrongShape` |
| [`microcode.py`](microcode.py) | `program_of(mask)`、`dispatch(program)`、`handlers(program)`、`body(program, at)`、`listing(program)` | 2,048 个程序字、每个命令字节分派到哪里，以及从处理程序到其返回的指令 |
| | `ISSUED` | 卡带写入的 19 个命令字节 |
| [`derived.py`](derived.py) | `reciprocal(part)`、`refined(part, value)`、`trig(part)`、`ask(part, command, words, answers)` | 芯片在 `$4000` 到 `$7FFF` 上的倒数，以及每个角度上的正弦和余弦。`refined` 在 200 条指令后仍未返回时抛出 `Runaway` |
| | `leading(value)`、`counted()`、`doublings(folded)`、`inverted(mantissas, negative)` | 前导位计数，以及为地面例程重新索引的倒数。对不是 16,384 项的表，`inverted` 会抛出 `ValueError` |
| | `write(where, values)`、`write_bytes(where, raw)`、`pieces(where)` | 写入并读回 32,768 字节的分片。没有任何分片时 `pieces` 抛出 `FileNotFoundError` |
| [`complete.py`](complete.py) | `domains(runs)`、`wanted(values)`、`filled(command, keys, answers, have)` | `$13` 和 `$18` 每个参数取到的所有值、这些值的所有组合，以及对没有任何录制包含的组合驱动芯片得到的答案 |
| [`routines.py`](routines.py) | `run(image, entry, words, answers)`、`asked(command, words, answers)`、`inputs(count, how_many, seed)` | 在 65816 模型上运行的一个汇编例程、芯片对同一问题的答案，以及带种子的随机参数。`run` 在 40,000 条指令后抛出 `TooLong` |

### 从芯片中读出的运算

| 模块 | 调用 | 返回 |
|:--|:--|:--|
| [`attitude.py`](attitude.py) | `matrix(sine, cosine, five, six)` | `$02` 构建的矩阵的九个单元，以其暂存地址 `$5A` 到 `$7C` 为键 |
| [`raster.py`](raster.py) | `answer(state, start, lines, table)`、`scanline(state, line, table)` | `$0a` 每行的四个答案字，按芯片的计算方式算出 |
| | `product`、`normalise`、`reciprocal`、`scaled`、`shortfall(got, want)` | 各个阶段，以及两个答案有多少行一致 |
| [`parameter.py`](parameter.py) | `GROUPS`、`CELLS`、`gathered(seen, slots)`、`fixed(runs)`、`mirrored(state)`、`sized(rows)` | 每个状态字跟随 `$02` 七个参数中的哪些。某个键给出两个状态时 `gathered` 抛出 `Disagreement`，矩阵不是两个字重复两次时 `mirrored` 抛出 `NotMirrored` |
| [`state02.py`](state02.py) | `packed(table)`、`checked(table)`、`rows(table)`、`stride(table)` | 把一张带键的表变成排好序的小端序字。行宽不一致时 `checked` 抛出 `Ragged`，有值超出一个字时抛出 `TooWide` |
| [`state02build.py`](state02build.py) | `gather(mask, where)`、`driven(part, sets)`、`tables(seen)`、`clamped(part)`、`checked(built)` | 三张状态表，以及某张表超过一个 32,768 字节的 bank 时抛出的 `TooBig` |

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

`product` 将两个带十五个小数位的有符号字相乘。`normalise` 左移直到第 15 位和第 14 位不同，并在结果旁返回移位次数。`scaled` 应用一个指数，并在 `$7FFF` 处钳位。该矩阵以第五个参数为角度 0、第六个参数为正弦和余弦都等于 `$5A82` 的角度构建。

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

各行按键排序，这样卡带可以用二分法找到一行，每行由其键字和随后的答案字组成。

### 表、镜像和补丁

| 模块 | 调用 | 返回 |
|:--|:--|:--|
| [`lutbuild.py`](lutbuild.py) | `rows_of(runs)`、`completed(built, runs)`、`chosen(built, calls, room)`、`gather(where)` | 每条命令的已录制答案，在芯片保持状态的地方以 `CARRIER` 为键，`$13` 和 `$18` 已补全，其余按每字节调用次数挑选 |
| | `encode(tables)`、`sliced(raw)`、`banks(pieces, first)`、`source(pieces, first_bank)` | 卡带读取时的表格式，从 `$99` 开始切分成 bank，跳过 `$7E` 和 `$7F`。某行会从奇数字节开始时 `encode` 抛出 `Uneven` |
| | `axes(built)`、`axes_source(found)` | 键为其各值所有组合的那些命令，以及计算出行号而不是搜索的代码 |
| | `CARRIER`、`COMPUTED`、`UNSTORABLE` | 承载者；靠运算作答的命令 `$00`、`$04`、`$08` 和 `$80`；以及 `$0a` |
| [`lut.py`](lut.py) | `KERNELS`、`expand(table, count)`、`blob(count)`、`cost(count)`、`image_bytes(count)` | 在整个输入上插值得到的四张表，以及它们的大小 |
| | `plan(census, command)`、`planned(census)`、`table(runs, command, carrier)`、`encode(table)` | 每条命令一张表，按范围或按已录制的集合索引，以及它的编码 |
| [`layout.py`](layout.py) | `runs(rom, least=256)`、`free(rom)`、`largest(rom)`、`fits(rom, wanted)`、`spread(rom, wanted)`、`must_grow(rom, wanted)` | `$FF` 或 `$00` 的连续段，形式为 `(start, end)`，它们的总量、最长的一段，以及某个大小能否放下 |
| [`patch.py`](patch.py) | `plan(rom, limit)`、`applied`、`spanned`、`hooked`、`rearmed`、`held`、`hooked_nmi`、`redirected`、`declared`、`checksummed`、`symbols(path)` | 该命令按顺序执行的每个步骤。`$07E84` 处所需的六个字节不为空时 `held` 抛出 `ArmGapTaken`，中断向量不指向 `$F0A0` 时 `hooked_nmi` 抛出 `VectorMoved` |

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

## 状态

在三份录制包含的每个问题上，每条有返回值的命令都与芯片的答案完全一致。剩下的是速度问题，记录在 [`OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md) 中。

| 部分 | 状态 |
|:--|:--|
| 转储识别，全部三个地区 | 按 SHA-256 与 [`artifacts.manifest.json`](artifacts.manifest.json) 对照 |
| 每个卡带在哪里访问芯片 | 两种访问形式都已覆盖，并与一份录制对照检查 |
| 卡带能发出哪些命令 | 每个镜像中 20 条，并与一份录制对照检查 |
| 芯片给出什么答案 | 运行芯片自身的微码 |
| 录制包含的参数组 | 三次运行共 73,341 个 |
| 芯片计算所依据的表 | 四张，1,280 字节，精确重建 |
| 无法用公式重现的三张表 | 从芯片中取得，294,912 字节 |
| `$02` 的状态，即 `$0a` 读取的全部内容 | 三张取自芯片的表，59,686 字节，在全部 6,980 个参数组上没有任何键对应两个答案 |
| `$00`、`$08` 和 `$04` | 65816 运算，在各 400 个随机参数组上与芯片完全一致 |
| 已录制答案表 | 12 条命令 |
| `$13` 和 `$18` | 在整个定义域上完整，由驱动芯片得出 |
| 查找 | 在每个已录制的问题上完全一致，全部三个地区 |
| 回退 | 回答每条命令，包括没有任何录制包含的键，且不会陷入循环 |
| `$0a` | 65816，完全一致：在全部三份录制的 60 个参数组上，43,440 个答案字中 43,440 个一致 |
| 经过重定向窗口的访问 | 200 处三字节访问各自替换为三字节调用，另有五段被整体替换 |
| 用读到的值做运算的长地址访问 | 七处已改道，六处 `adc`，一处 `eor` |
| 游戏自身经由窗口 bank 进行的工作 RAM 读写 | 全部 31 处已改道。[`OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md) 第 30 节 |
| 演示 | 能飞行，能绘制地面，并在游戏帧 405 之前，即对比运行结束时，一直与零售版卡带的飞行轨迹一致。工作 RAM 每帧相差 30 到 60 字节，其中 22 字节每帧都不同，这 22 字节中有十二字节是游戏复制到工作 RAM 中的一次已打补丁的调用 |
| 仪表盘 | 每个画面上都有绘制。整个演示中屏幕亮度的离散范围为 0.05，与零售版卡带的水平相同。第 32 节 |
| 穿过仪表盘的条带 | 出现在 2.2% 的帧上。第 48 节 |
| `$02` 留下的十个字 | 通过计算或从覆盖整个键的表中读取，十个字在横跨整个演示的 596 帧上都与芯片完全一致 |
| 镜像大小 | 会扩容，但在低位映射卡带可寻址的范围内 |

### 速度

| 测量项 | 值 |
|:--|:--|
| 一次 `$0a` 调用，在演示的 149 帧上取平均 | 77,044 个处理器周期 |
| 非首次的一次 `$0a` 调用 | 130,147 个周期，在一次飞行的 24 个状态上波动在 3% 以内 |
| 距离与上一行相同、因而直接复制答案的行 | 63.6% |
| 每行六次查表乘法占 `$0a` 的比例 | 54.7% |
| 构建四张乘法表，在任何帧之外 | 62,665 个周期 |
| 对一份录制中的 600 个键做一次查找 | 1,566,405 个周期 |
| 一次读取耗费 8 个主时钟时的一帧 | 44,671 个处理器周期 |
| 芯片，每次调用游戏被阻塞的实际时间 | 几十个周期到约 250 个，中位帧有 43 次调用，约 2,700 个 |
| `$00`、`$08` 和 `$04` 的运算 | 398、920 和 833 个周期 |

以上均在处理器模型上测量，从未在主机上测量。一次改动会改变测量窗口打开时演示所处的位置，因此主机的帧率计与工作量并不单调相关：给地面绘制加上 25,566 个周期的无用工作，反而使它报告了更好的帧率。第 36 到 39 节以及第 49、51 和 52 节记录了这些运行。

在一个完整的游戏帧内，按程序计数器采样并对照汇编器的行映射：

| 位置 | 占比 |
|:--|--:|
| 地面 | 46.8% |
| 已录制答案的搜索 | 20.6% |
| 游戏自身的代码 | 15.4% |
| 端口 | 11.2% |

两条不需要搜索的命令由 [`lutbuild.py`](lutbuild.py) 生成为计算出行号的代码。其中一条每个游戏帧被询问 9.4 次。第 50 节。

### 表覆盖了游戏的多少部分

用部分录制构建，再用其余部分提问：

| 提问内容 | 命中率 |
|:--|--:|
| 构建所用的问题 | 100% |
| 同一吸引模式演示的另一份录制 | 93.4% |
| 一份录制的后半部分，表学习了它的前半部分 | 11.2% |

三份录制都是同一段吸引模式演示，所以中间的数字衡量的是重复程度。最后一个数字是玩家做了演示中从未做过的事情时会遇到的情况。在这个数字上，`$10` 命中 10.9%，`$06` 为 0%。`$06` 占游戏所有调用的 31.7%。

`$13` 和 `$18` 不按这种方式测量，因为它们不会未命中。它们的参数是量化的：`$13` 的某个字跨度为 32,769，只取七个值，所以按跨度估算是 5.48e17 行，按取值估算是 1,512 行。所有组合都已从芯片中驱动得出，录制中的全部 248 行以同样方式驱动时结果完全相同。

`$10` 的定义域有 4,996 种组合，没有补全。仅按其键驱动时，100 次中有 83 次重现录制结果，所以填入的行中会有 17% 是错的。缺失的行会回退到代码，错误的行不会。

### 查找给出的答案

在处理器模型上对照三份录制驱动，每个地区每条命令四十个问题：

| 命令 | 正确 | 错误 |
|:--|--:|--:|
| `$00` `$02` `$03` `$06` `$08` `$0c` `$0d` `$0e` `$10` `$13` `$14` `$1b` `$28` | 各 120 | 0 |
| `$04` | 40 | 0 |
| `$18` | 10 | 0 |

录制中 `$04` 和 `$18` 的不同问题较少。

## 测量了什么

### 一个替代实现覆盖全部三个地区

在代码中查找向数据端口的存储，涵盖卡带使用的两种形式，USA 镜像中有 208 处，日本镜像中有 218 处，欧洲镜像中有 208 处。从中读出的二十个命令字节在三者中是同样的二十个。

长地址形式在每个地区都落在两个地址上：`$3f:8000` 处 84 条指令，`$3f:c000` 处 9 条，三者的数量相同。这是同一个驱动程序出现了三次，所以一个地区的替代实现也就是另外两个地区的替代实现。

### 驱动程序的大部分对长地址形式的搜索不可见

热路径用 `pea $003f` 和 `plb` 设置一次数据 bank，然后使用只写两个字节、不指明 bank 的绝对地址存储。对照日本镜像的一份录制测量，该录制带有每次访问的程序计数器：

| | 指令 | 长地址形式 | 绝对地址 | 长地址形式传送的字节占比 |
|:--|--:|--:|--:|--:|
| 向芯片写入 | 118 | 40 | 78 | 62.2% |
| 从芯片读取 | 47 | 13 | 34 | 7.9% |

[`commands.py`](commands.py) 两种都能读取。游戏中最热的循环是 `plb` 之后的 `sta $8000`，接着是 176 次轮询并读取。

按编码搜索还会报告并非指令的字节。在 USA 镜像中，122 个长地址形式匹配里有 29 个位于 bank `$30` 到 `$3e` 中 29 个不同的地址上，每处一个匹配。日本有 28 个，欧洲有 30 个，三个总数之间的差异全部来自它们。

### 每条命令读取多少个字

通过芯片的协议测量：一条命令如果少写一个它需要的字，仍然会回显；多写一个，就不再应答。数量就是从这个沉默处往回退一步。它还用运算来核对：命令 `$00` 给出其两个字带十五个小数位的有符号乘积，`0x1234 x 0x5678 -> 0x0C4C`。

256 个命令字节中有四十五个会作答。

| 输入字数 | 输出字数 | 命令数 | 包含全部答案的表 |
|--:|--:|--:|:--|
| 1 | 1 | 2 | 131,072 字节，能放下 |
| 2 | 1 | 2 | 8,589,934,592 字节，是 96 Mbit 镜像的 683 倍 |
| 3 | 1 | 14 | 562 TB |
| 4 | 1 | 7 | 更大 |
| 5 | 1 | 17 | 更大 |
| 6 | 12 | 1 | 更大 |
| 10 | 1 | 2 | 更大 |

有两条命令可以存下全部答案。其余四十三条中最小的也是 96 Mbit 镜像的 683 倍。上表计算的是芯片输入定义域的大小。游戏实际询问的要小得多，下面几节计算的是它的大小。

### 游戏询问什么

日本镜像在无输入状态下运行 12,000 帧，让吸引模式演示自行飞行，期间从 30 个调用点发出了 257,189 条命令。NTSC 镜像在第 10,418 帧之后不再访问芯片，而 PAL 镜像在第 11,999 帧时仍在飞行，这就是为什么欧洲版会发出 `$04` 而另外两个从不发出。

| 命令 | 占比 | 发出次数 | 调用点 | 作用 |
|:--|--:|--:|--:|:--|
| `$06` | 28.9% | 74,261 | 2 | |
| `$13` | 25.4% | 65,332 | 1 | |
| `$00` | 15.0% | 38,668 | 10 | 有符号乘法，靠计算 |
| `$11` | 4.7% | 12,136 | 2 | |
| `$0a` | 2.7% | 6,946 | 1 | 以一个被读取 176 次的数据流作答 |
| 其余 13 条 | 23.3% | 59,846 | 14 | |

### 在发出命令的调用点切分录制

`$0a` 以一个卡带读取 176 次的数据流作答，而芯片在该数据流期间仍接受写入。于是一个交换内部的读取看起来像是交换的结束，按这种方式切分时，有十分之一的段包含来自相距超过 32 字节的代码的写入。

[`exchanges.py`](exchanges.py) 改为在命令调用点切分。只访问数据端口低半部分的程序计数器发出的是命令，访问两个半部分的程序计数器写入的是参数字。

在全部三次运行中：19 条命令共 73,341 个不同参数组，每个存一个答案时为 586,728 字节。

| | 命令数 | 行数 | 字节 | 流量占比 |
|:--|--:|--:|--:|--:|
| 内联比较链 | 5 | 22 | 176 | 30.5% |
| 表 | 13 | 46,832 | 374,656 | 54.3% |
| 靠计算，因为是乘法 | 1 | 无 | 0 | 15.8% |

### 芯片计算所依据的内容

uPD77C25 在程序旁边保存了 1024 个字的数据 ROM。[`tables.py`](tables.py) 根据公式重建每个候选表并进行搜索。其中有四张表，逐字一致：

| 表 | 字数 | 公式 | 字节 |
|:--|--:|:--|--:|
| 倒数 | 128 | `2^22 / (128 + k)`，四舍五入并钳位 | 256 |
| 正弦 | 128 | `sin(pi k / 128) x 32768`，截去小数 | 256 |
| 余弦 | 128 | `cos(pi k / 128) x 32768`，截去小数 | 256 |
| 反余弦 | 256 | `acos(k / 256) x 32768 / pi` | 512 |
| | | **合计** | **1,280** |

没有平方根，也没有反正切。两个掩模版本都带有同样的四张表，DSP-1B 中有三张位置低两个字。

### 每个参数的取值范围

[`exchanges.py`](exchanges.py) 报告每个参数位置的最小值、最大值和不同值的数量：

| 参数位置的情况 | 命令数 | 表按什么索引 |
|:--|--:|:--|
| 一个或少数几个值 | 5 | 按值，内联 |
| 几千个，填满其范围 | 2 | 按范围，2^18 和 2^20 行 |
| 至少有一个覆盖整个字 | 12 | 没有稠密的索引 |

命令 `$0d` 在三个位置上各取约四千个不同值，每个都覆盖完整的 0 到 65,535。按范围建表将有 2^48 行，几乎全是没人会发送的输入，所以这两个数字总是一起报告。

### 芯片保持状态

十六条会作答的命令中有七条对相同参数给出不同答案，因为一条读取另一条命令所加载矩阵的命令，其结果不是自身参数的函数。`$0e` 在每份录制中只取一个参数组，却给出 6,260 种不同的答案。

七条中的六条在键中再带上某条更早命令的参数后就变得确定，这就是 [`lutbuild.py`](lutbuild.py) 中的 `CARRIER`：

| 命令 | 以其参数和最近一次的哪条命令为键 |
|:--|:--|
| `$03` | `$14` |
| `$06`、`$0d`、`$0e` | `$02` |
| `$13`、`$1b` | `$11` |

`$0a` 是第七条。没有任何更早的命令能单独、或以任意两条或三条的组合确定它。存储每个不同的完整答案需要 16,762,160 字节，存储四字步进则在任何索引之前就有 538,583 个不同步进。因此它改为计算：每行一次规格化、一次倒数、两次乘法和两次移位，逐阶段从芯片的程序中读出，并与其寄存器对照核对。第 22 节。

### 表编码后的大小

[`lutbuild.py`](lutbuild.py) 将每条命令的行按键排序，这样卡带可以用二分法找到一行。根据三份录制，在补全 `$13` 和 `$18` 之前：

| 命令 | 键 | 行数 | 键字数 | 答案字数 | 字节 |
|:--|:--|--:|--:|--:|--:|
| `$06` | 参数和最近一次 `$02` | 75,278 | 10 | 3 | 1,957,228 |
| `$0d` | 参数和最近一次 `$02` | 6,557 | 10 | 3 | 170,482 |
| `$02` | 参数 | 6,980 | 7 | 4 | 153,560 |
| `$0e` | 参数和最近一次 `$02` | 6,980 | 9 | 2 | 153,560 |
| `$03` | 参数和最近一次 `$14` | 5,268 | 9 | 3 | 126,432 |
| `$14` | 参数 | 4,406 | 6 | 3 | 79,308 |
| `$28` | 参数 | 6,182 | 3 | 1 | 49,456 |
| `$1b` | 参数和最近一次 `$11` | 2,986 | 7 | 1 | 47,776 |
| `$0c` | 参数 | 3,480 | 3 | 2 | 34,800 |
| `$10` | 参数 | 2,498 | 2 | 2 | 19,984 |
| `$13` | 参数和最近一次 `$11` | 244 | 7 | 3 | 4,880 |
| `$18` | 参数 | 4 | 4 | 1 | 40 |
| | | | | **合计** | **2,797,956** |

这相当于 86 个 32,768 字节的 bank。每行既带答案也带键，由于芯片保持状态，`$06` 用十个键字换三个答案字。

### 录制能说明什么、不能说明什么

录制说明的是游戏做了什么，从不说明游戏能做什么。大多数参数来自飞机的姿态，几乎每帧都取新值，所以没有哪份录制显示其输入集合已经收敛。因此每条命令在表后面都有一个代码实现的回退。

读取代码回答了另一半问题。[`commands.py`](commands.py) 从每个镜像中读出 20 个命令字节，欧洲版多读出一个 `$80`。对照日本录制，在实际运行过的 30 个调用点中它与其中 27 个一致，没有矛盾，另外三个无法判断。对照欧洲录制，36 个中 33 个一致，没有矛盾。

| | 命令 |
|:--|--:|
| 从代码中读出，全部三个镜像 | 20 |
| 欧洲版还读出 | `$80` |
| 日本录制发出的 | 18 |
| 欧洲录制发出的 | 19 |
| 读出但从未见到运行 | `$21`、`$23` |

`$80` 让芯片回到等待命令的状态。卡带在 `$0702a` 处连续写入它 128 次以清空芯片。

### 零售版镜像中的空间

[`layout.py`](layout.py) 测量由同一个字节重复组成、长度 256 字节或以上的连续段：

| 地区 | 这些连续段中的空闲空间 | 最长的单个连续段 |
|:--|--:|--:|
| USA | 63,122 | 4,249 |
| 日本 | 74,207 | 8,395 |
| 欧洲 | 63,122 | 4,249 |

每个镜像都能整块容纳四张 1,280 字节的表。已录制答案表放不下，所以镜像需要扩容。同一字节重复的连续段只是没有被使用的证据，所以在往候选连续段中放入任何内容之前，都要对照驱动程序普查进行检查。

<a id="the-dumps"></a>

## 转储

按 No-Intro 的命名。每个摘要都针对不含拷贝机文件头的完整文件。以 SHA-256 为准，CRC32 用于与仍以它为键的数据库交叉核对。

| 文件 | 读取路径 | 大小 |
|:--|:--|--:|
| Pilotwings，USA | `external/roms/pilotwings-usa.sfc` | 524,288 |
| Pilotwings，日本 | `external/roms/pilotwings-jp.sfc` | 524,288 |
| Pilotwings，欧洲 | `external/roms/pilotwings-eur.sfc` | 524,288 |

| 地区 | SHA-256 | CRC32 |
|:--|:--|:--|
| USA | `03d0127f5de3237e22ad00de0c20763274da7b71142dde693240ac96d10983a3` | `266C44ED` |
| 日本 | `d1845de22c3c7f2606bda20e09c8f7a78f92f5cbbb6bfe01f96a1d1e84b30394` | `77871727` |
| 欧洲 | `f70a72f3d3a65497cdc4d849877a29cf4f7bd10439bb7f5cb8675cdfc0e706d4` | `DEF45776` |

三者都声明版本为 `0x00`。基于本游戏制作的 Nintendo Campus Challenge 卡带同样是 524,288 字节，声明同样的芯片组 `0x03`，带有同样的内部标题 `PILOTWINGS`。只有它的映射字节和摘要能把它区分开，这就是为什么识别只看摘要。

## 底层模型

| 模型 | 子模块 | 验证依据 |
|:--|:--|:--|
| 65816 | [mos65xx-python](https://github.com/gufranco/mos65xx-python) | 逐操作码的测试集，5,120,000 个用例 |
| DSP-1 | [snes-dsp-python](https://github.com/gufranco/snes-dsp-python) | 运行芯片自身的微码 |
| 卡带映射 | [snes-mapper-python](https://github.com/gufranco/snes-mapper-python) | 一个真实卡带库中的每种文件头组合 |
| ROM 镜像 | [snes-rom-image-python](https://github.com/gufranco/snes-rom-image-python) | 同一个库，经重写并检查 |
| 驱动程序 | [snes-driver-python](https://github.com/gufranco/snes-driver-python) | 卡带代码在哪里访问其协处理器 |

没有图形模型。这块芯片只计算数字，从不涉及图块。

上面所有周期数都来自 65816 模型：它逐周期驱动总线，所以一个例程的开销就是它实际耗费的周期。它启动时内存和寄存器中是可重现的打乱值而不是零，所以读取从未写入过的内容会表现为错误的答案。

## 所有内容在卡带中的位置

低位映射卡带包含 bank `$00` 到 `$7D`。本项目添加的所有内容都通过 `$80` 及以上的镜像区读取，设置 `$420D` 后，那里的读取只需六个主时钟，而不是八个。

| 内容 | Bank | 读取地址 |
|:--|:--|:--|
| 原样发行的游戏 | `$00`-`$0F` | |
| 替代实现的代码 | `$10` | `$90` |
| 从芯片中取得的正弦和余弦 | `$11`-`$18` | `$91`-`$98` |
| 已录制的答案 | `$19`-`$6F` | `$99`-`$EF` |
| `$02` 的状态，供 `$0a` 读取 | `$70`-`$72` | `$F0`-`$F2` |
| 从芯片中取得的倒数 | `$73` | `$F3` |
| 游戏被重定向的访问所落入的窗口 | `$7D` | `$7D` |

回答全部十二条已录制命令需要 87 个 bank，其中 60 个用于 `$06`。只要能换来保真度、稳定性或速度，镜像可以扩容到 96 Mbit。`$7D` 以上的每个 bank 都需要窗口化布局，所以镜像在可能时保持在其下方。2 MiB 和 4 MiB 的镜像在文件头大小字节匹配后能以完全相同的方式启动并运行演示，[`patch.py`](patch.py) 根据镜像长度设置该字节。

## 结果对不对

有两个判定依据，这里没有任何东西自行计算 DSP-1 的结果。零售版卡带决定问什么：一条命令和一个参数组之所以是一个问题，是因为零售版卡带会发送它们。芯片的微码决定答案，通过 [snes-dsp-python](https://github.com/gufranco/snes-dsp-python) 运行。

| 断言 | 验证依据 | 位置 |
|:--|:--|:--|
| 转储就是那份转储 | [`artifacts.manifest.json`](artifacts.manifest.json) 中的 SHA-256 | [`tools/identify.py`](tools/identify.py) |
| 卡带在哪里访问芯片 | 对代码的读取与一次运行的录制双向对照检查 | [`commands.retail.test.py`](commands.retail.test.py)、[`sites.retail.test.py`](sites.retail.test.py) |
| 一个例程给出什么答案 | 向芯片提出同样的问题 | [`routines.retail.test.py`](routines.retail.test.py)、[`raster.retail.test.py`](raster.retail.test.py)、[`attitude.retail.test.py`](attitude.retail.test.py) |
| 四张表 | 微码的数据 ROM，逐字一致 | [`tables.retail.test.py`](tables.retail.test.py) |
| 补丁 | 零售版镜像 | [`patch.retail.test.py`](patch.retail.test.py) |

需要转储或微码的检查放在十个 `*.retail.test.py` 文件中，共 96 个测试，缺少其中任一项时会报告自身被跳过。在两者都有的机器上，门禁检查像对待其他文件一样按 100% 测量它们。CI 无法持有其中任何一项，因此以 `RETAIL_INPUTS=absent` 运行，覆盖率报告不包含它们。

本项目重现的是 DSP-1，从不是 DSP-1B。吸引模式演示是一段按键输入的录制，在 DSP-1B 修正过的运算下，飞机按同样的输入会撞向地面。零售电路板上装的是哪个掩模版本，无法从转储中读出。这个问题以及其他所有比看上去更窄的断言都记录在 [`OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md) 中，每条都附有能够解决它的测量方法。

## 参与开发

| 需要 | 位置 |
|:--|:--|
| 每项门禁检查及其运行顺序 | [CONTRIBUTING.md](CONTRIBUTING.md) |
| 面向编程代理的同样内容 | [AGENTS.md](AGENTS.md) |
| 本仓库与同系列其他仓库共享的标准 | [FAMILY.md](FAMILY.md) |
| Bug 报告 | [GitHub Issues](https://github.com/gufranco/snes-pilotwings-nochip/issues) |
| 安全报告 | [SECURITY.md](SECURITY.md) |

```bash
./run.sh --gates
```

44 个文件共 1,093 个测试，每个模块旁边有一个 `<module>.test.py`。覆盖率是一项硬性门禁检查，要求语句和分支均为 100%，在 [`pyproject.toml`](pyproject.toml) 中设置。提交遵循 Conventional Commits，semantic-release 据此确定版本。

注释只出现在汇编代码中：入口和出口状态、寄存器宽度，以及每个地址的来源。Python 源码中没有注释。

切勿在 issue 中附加卡带或微码镜像，也切勿链接到可以下载它们的地方。摘要能识别一个文件，而不携带它。

## 参考资料

- No-Intro，提供三份零售版转储的名称和摘要。
- commit `2971061cf07fdc6fc7d18883edf4e648eb16a6d2` 处的 snes9x，https://github.com/snes9xgit/snes9x ，由 [`Dockerfile`](Dockerfile) 构建，用于录制每次端口访问。这些录制是关于该模拟器的 DSP-1 的证据，这就是为什么查找是对照芯片自身的微码检查，而不是对照这些录制。
- asar v1.81，https://github.com/RPGHacker/asar ，由 [`Dockerfile`](Dockerfile) 构建。
- neviksti 的无芯片 Star Ocean 改版，提供了大于低位映射卡带地址空间的镜像的寻址规则。
- Nintendo EAD 和 Argonaut，制作了这款游戏。

## 引用本项目

[CITATION.cff](CITATION.cff) 在每次发布时由 [`scripts/set-version.sh`](scripts/set-version.sh) 更新，该脚本也负责为 [`version.py`](version.py) 写入版本号。

## 许可证

MIT。见 [LICENSE](LICENSE)。它涵盖工具、汇编代码和本文档，不授予对游戏的任何权利。这里不分发任何 ROM 数据：所有操作都针对你自己提供的转储。
