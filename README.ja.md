# DSP-1なしのPilotwings

3つの地域版すべてについて、DSP-1コプロセッサをカートリッジ内のテーブルと65816コードに置き換えたPilotwingsのイメージをビルドするツール群です。ゲームが何を問うかは市販カートリッジに、すべての答えはチップ自身のマイクロコードに照らして検証しています。

[English](README.md) | 日本語 | [简体中文](README.zh-Hans.md) | [繁體中文（香港）](README.zh-HK.md)

[![CI](https://github.com/gufranco/snes-pilotwings-nochip/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/snes-pilotwings-nochip/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**16**個のコマンドを、**3**つの地域版の記録に含まれるすべての質問でチップと照合して回答、誤答**0**件、`$0a`の地面ワードは**43,440**個中**43,440**個が完全一致、テスト**1,055**件、全モジュールで命令と分岐のカバレッジ**100%**、標準ライブラリ以外の依存はなく、固定されたサブモジュールが**5**個です。

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

最初のループは、DSP-1がデータROMに持つ4つのテーブルを式から再構築します。これは[`tables.py`](tables.py)がマイクロコードの中から探すものです。2番目は、1つ、2つ、または3つの引数ワードを読むコマンドについて、すべての答えを保持するテーブルの大きさを求めます。1ワードなら96 Mbitのカートリッジに収まり、2ワードでは収まりません。この行が、置き換えがゲームの問う答えを保存し、残りを計算する理由です。

## インストール

### 手順

何もない状態から動くチェックアウトまで5つの手順です。手順4のドクターが最初の3つを確認します。

1. **Python、git、アセンブルするならDockerをインストールします。**

   | | Windows | macOS | Linux |
   |:--|:--|:--|:--|
   | Python 3.12以降 | `winget install Python.Python.3.12` | `brew install python@3.12` | ディストリビューションの`python3`パッケージ |
   | git | `winget install Git.Git` | `xcode-select --install` | ディストリビューションの`git`パッケージ |
   | Docker（アセンブラと記録用エミュレーターだけに必要） | `winget install Docker.DockerDesktop`を実行し、Docker Desktopを起動 | Docker Desktop、または`brew install colima docker`の後に`colima start` | Docker Engineを入れ、`sudo systemctl start docker` |

   Windowsでは、このページの`python3`を`py -3.12`に置き換えてください。

2. **リポジトリをクローンします。ダウンロードはしないでください。**

   ```bash
   git clone --recurse-submodules https://github.com/gufranco/snes-pilotwings-nochip.git
   cd snes-pilotwings-nochip
   ```

   > [!CAUTION]
   > 動くコピーを得る方法はクローンだけです。GitHubの緑の**Code**ボタンには**Download ZIP**もありますが、ZIPはここでは決して動きません。このプロジェクトが使う5個のモデルはgitのサブモジュールとして固定された別のリポジトリで、ZIPにはどれも含まれず、後から追加することもできません。ドクターはそのようなコピーをダウンロードしたアーカイブとして報告します。削除してクローンしてください。`--recurse-submodules`なしでクローンした場合は、`git submodule update --init --recursive`でその場で直せます。

3. **ダンプを`external/roms/`に置きます。** 名前は[ダンプの一覧](#the-dumps)のとおり`pilotwings-usa.sfc`, `pilotwings-jp.sfc`, `pilotwings-eur.sfc`です。マイクロコードは`external/firmware/`に置きます。その後で確認します。用意した各ダンプが`ok`と表示されるはずです。

   ```bash
   python3 tools/identify.py
   ```

4. **ドクターを実行します。** チェックアウト、各モデル、各ダンプを確認し、最後に次に実行するものを示します。

   ```bash
   python3 doctor.py
   ```

   ```
     N checks, nothing to report
     next: python3 tools/identify.py
   ```

   `!`の付いた行は、その下の行にすべきことを書いています。ドクターが見つける設定の誤りは次のとおりです。

   | ドクターの表示 | すること |
   |:--|:--|
   | `checkout: no git metadata` | フォルダーを削除してクローンする（手順2） |
   | `... is not checked out` | `git submodule update --init --recursive` |
   | `cartridge ...: missing` | 手順3 |

5. **ひとつのビルドコマンドはまだありません。** このプロジェクトは非常に実験的で、インターフェースのコマンドでゲームを記録し、表を作り、イメージにパッチを当てます。多くの問題が予想されます。報告を歓迎します。

### 必要なものとドクター

| 必要なもの | バージョン |
|:--|:--|
| Python | 3.12以降 |
| git | 任意、5つのサブモジュールの取得に使用 |
| ご自身のカートリッジのダンプ | 各524,288バイト、[ダンプ](#the-dumps)の名前で`external/roms/`に配置 |
| ご自身が持つDSP-1マイクロコードのコピー | 8,192バイト、`external/firmware/dsp1.bin`および`external/firmware/dsp1b.bin`として配置 |
| Docker | 任意、[`asm/`](asm/)のアセンブラと[`emu/`](emu/)の記録用エミュレータのビルドにのみ使用 |

パッケージインデックスからは何もインストールせず、何もダウンロードしません。このプロジェクトが自身を照合する5つのモデルは、リポジトリのルートにあるgitサブモジュールです。download-zipリンクから得たソースアーカイブにはそのどれも含まれず、ドクターはそのようなフォルダーをアーカイブとして報告します。

マイクロコードは`external/firmware/`の代わりに`UPD7725_FIRMWARE_DIR`が指す任意の場所に置けます。マイクロコードがないと、チップを動かすチェックはすべて実行対象がなかったと報告します。

ドクターは、マシン、このプロジェクトのバージョン、フォルダーがgitのクローンかどうか、各モデルとそのバージョン、マイクロコードが動くかどうか、2つのマスクのうちどちらがあるか、各ダンプの状態、そして各モデル自身のドクターの報告をそのモデル名の下に出力します。すべてのチェックが通れば0で、そうでなければ1で終了します。バグ報告には出力全体を貼り付けてください。ダンプもマイクロコードもない再帰クローンの直後では、次の行で終わります。

```
  5 of 93 checks did not pass
  next: fix the first line marked ! above, then run python3 doctor.py again
```

この5つは、マイクロコードの欠如、DSPモデルがイメージを持たない2つのマスク、そして2つのサブモジュールがそれぞれ同梱する空の`cartridges`ディレクトリです。

## インターフェース

リポジトリのルートから実行する一連のスクリプトと、それらを構成するモジュールです。引数を取るスクリプトは、引数がないと使い方の行を出力して2で終了します。

### コマンド

| コマンド | 引数 | 動作 | 終了コード |
|:--|:--|:--|:--|
| `python3 doctor.py` | なし | マシンとモデルの連鎖全体を報告します | 0は正常、1はチェックが通らなかったとき |
| `python3 tools/identify.py` | なし | `external/roms/`内の各ファイルを[`artifacts.manifest.json`](artifacts.manifest.json)と照合し、macOS、Linux、WindowsでSHA-256を計算するコマンドを出力します | 0はすべてのダンプが一致するか存在しないとき、1は1つでも誤っているとき |
| `python3 exchanges.py <trace>` | 記録 | 記録を各コマンドサイトで区切り、各コマンドについてそのやり取り、割合、異なる引数セット、サイト、答え方を出力します | 0、2 |
| `python3 tables.py <microcode image>` | 8,192バイトのイメージ | イメージのデータROMから4つのテーブルを見つけ、それぞれの開始ワードを出力します | 0、2 |
| `python3 microcode.py <mask>` | `dsp1`または`dsp1b` | 256個すべてのコマンドバイトについてマイクロコードのディスパッチをたどり、各ハンドラをカートリッジが書き込むコマンドとともに出力します | 0、2 |
| `python3 layout.py <image> <bytes wanted>` | イメージとサイズ | 256バイト以上続く`$FF`または`$00`の連なりを見つけ、イメージを拡張せずにそのサイズを収められるかを示します | 0、2 |
| `python3 lut.py [<rows>]` | テーブルごとの行数、デフォルトは65,536 | 入力全体にわたって表にした4つのテーブルの大きさを求めます | 0 |
| `python3 derived.py <mask> [<directory>] [--reindex]` | マスク、出力ディレクトリ、デフォルトは`build` | チップを動かして`$4000`から`$7FFF`までの逆数と65,536個の角度での正弦と余弦を求め、すべてのワードについて先頭の倍加回数を数えます。`reciprocal`、`recip-up`、`recip-down`、`recip-exponent`、`leading`、`sine`、`cosine`を、`<stem>-<n>.bin`という名前の32,768バイトの断片として書き出します。`--reindex`は、ディスク上にある逆数から3つの`recip-`テーブルを再構築します | 0、2 |
| `python3 state02build.py <mask> [<directory>]` | マスク、記録を保持し出力を受け取るディレクトリ、デフォルトは`build` | 記録に含まれるすべての引数セットで`$02`を動かし、3つの状態テーブル、`state02-map.asm`、`state02-data.asm`、65,536個の角度でのクランプされた余弦を書き出します | 0、2 |
| `python3 lutbuild.py <mask> [<directory>]` | マスク、出力ディレクトリ、デフォルトは`build` | `build/trace-usa.bin`、`build/trace-jp.bin`、`build/trace-eur.bin`から記録済みの答えのテーブルを作り、DSP-1を動かして`$13`と`$18`を補完し、`lut-<n>.bin`、`lut-map.asm`、`lut-axes.asm`を書き出します | 0、2 |
| `python3 patch.py <rom> <symbols> <out> <game bytes> [--slow]` | アセンブル済みのイメージ、`name hex`行からなるシンボルファイル、出力パス、イメージ内のゲームの長さ | カートリッジがチップに行うすべてのアクセスを置き換え先に向け、ヘッダからコプロセッサを外し、サイズバイトを設定し、`--slow`が指定されない限り高速ROMビットを設定し、チェックサムを書き直します | 0、1はイメージがチップに一度もアクセスしないとき、2 |
| `python3 tools/cycles.py <image> <assembler log> [<routine>] [<snapshot>]` | イメージ、アセンブラが出力したシンボル、デフォルトのルーチンは`ground_block`、デフォルトのスナップショットは`build/nb2/wram-000300.bin` | 65816モデル上でルーチンを1回呼び出し、そのサイクル数と命令数を出力します | 0、1はスナップショットがないとき、2 |
| `python3 tools/profile.py <image> <symbol file> [<routine>] [<snapshot>] [--built]` | 上と同じ、スナップショットがすでに構築済みのテーブルを保持しているときは`--built`を追加 | 1回呼び出し、そのサイクルを各命令が属するラベルごとに分けて上位16件を出力します | 0、1はスナップショットまたはラベルがないとき、2 |

```bash
python3 tables.py external/firmware/dsp1.bin
```

```
  table        words   at     formula
  reciprocal     128    101  2^22 / (128 + k), rounded and clamped
  sine           128    280  sin(pi k / 128) x 32768, fraction cut off
  cosine         128    408  cos(pi k / 128) x 32768, fraction cut off
  arccosine      256    542  acos(k / 256) x 32768 / pi

  4 of 4 carried, 1,280 bytes to reproduce them all, against 131,072 for one table over a whole input
```

同じコマンドを`external/firmware/dsp1b.bin`に対して実行すると、正弦、余弦、逆余弦は2ワード下の278、406、540に、逆数は101に見つかります。

### 記録用エミュレータ

[`emu/`](emu/)は`pwemu`をビルドします。これはコミット`2971061cf07fdc6fc7d18883edf4e648eb16a6d2`のsnes9xに、DSP-1のすべてのポートアクセスに対するフックを加え、最小限のlibretroフロントエンドの背後に置いたものです。

```bash
docker build -t pwemu emu
docker run --rm -v "$PWD:/work" -e PWTRACE=build/trace-usa.bin pwemu external/roms/pilotwings-usa.sfc 12000
```

| 入力 | 意味 |
|:--|:--|
| `<rom> <frames>` | イメージと実行するフレーム数 |
| `PWTRACE` | バイナリのポートログのパス |
| `PWSCRIPT` | 入力スクリプト、1行に1つの`frame button...`、ボタン名は`up`、`down`、`left`、`right`、`a`、`b`、`x`、`y`、`l`、`r`、`start`、`select` |
| `PWRAM` | どのフレームも変更しなかったワークRAMのすべての連なりを`start end length`として受け取るパス |
| `PWPC` | 1フレームに1回サンプリングしたプログラムカウンタを受け取るパス |

`RESULT load=ok frames=<n> delivered=<n> accesses=<n> brightness=<x>`で終わって0で終了するか、イメージを読めないか読み込めないときは1で終了します。

ポートログの各レコードは12バイトのリトルエンディアンで、32ビットのフレーム、32ビットのバンク付きプログラムカウンタ、16ビットのポートアドレス、読み込みなら1で書き込みなら0、そして移動したバイトからなります。[`exchanges.py`](exchanges.py)と[`census.py`](census.py)がこの形式を読みます。

[`emu/native.cpp`](emu/native.cpp)は同じ記録を実行時に読み込むlibretroコアで行い、`native <core> <rom> <frames>`とします。[`emu/play.cpp`](emu/play.cpp)はコア上でウィンドウを開き、`play <core> <rom>`とします。

### アセンブラ

[`asm/Dockerfile`](asm/Dockerfile)はasar v1.81をビルドします。[`asm/nochip.asm`](asm/nochip.asm)がエントリファイルです。置き換えをバンク`$10`に配置し、[`asm/`](asm/)内の他のすべての`.asm`ファイルをインクルードし、上のスクリプトが`build/`に書き出すテーブルを読み込みます。出力される`SYM <name> <address>`行を[`tools/cycles.py`](tools/cycles.py)が読みます。

### ダンプ、バージョン、その下にあるモデル

| モジュール | 呼び出し | 戻り値 |
|:--|:--|:--|
| [`dumps.py`](dumps.py) | `artifacts()` | 3つの`Artifact`レコード。`name`、`region`、`filename`、`declares`、`accepted`、`provenance` |
| | `identify(data, digest=None)` | SHA-256が一致する`Artifact`、または`None` |
| | `identify_digest(digest)` | 同じものを、計算済みのダイジェストから |
| | `diagnose(data, digest=None)` | `kind`、`detail`、`repair`を持つ`Finding`。`kind`は`match`、`copier-header`、`wrong-size`、`unrecognised`のいずれか |
| | `digest_commands(filename)` | `macOS`、`Linux`、`Windows`用のSHA-256コマンド |
| | `manifest()`、`through()`、`not_this()` | マニフェスト、その出典、拒否すべきとして挙げるファイル |
| [`version.py`](version.py) | `VERSION`、`stamped(name, release=None)` | リリースと、そのリリースのイメージが持つファイル名 |
| [`hardware.py`](hardware.py) | `install(environment=None)` | すべてのモデルを`sys.path`に追加し、`external/firmware/`を`UPD7725_FIRMWARE_DIR`に加え、その変数を返します |
| | `load(package)` | モデルパッケージ。`mos65xx`、`snesdsp`、`mapper`、`romimage`、`snesdriver`、`upd7725`のいずれか |
| | `root_of(package)` | モデルのディレクトリ。それ以外の名前は`UnknownPackage`を送出します |
| [`tools/identify.py`](tools/identify.py) | `look(artifact, root)`、`judge(artifact, data)` | `region`、`filename`、`ok`・`absent`・`wrong`のいずれかの`state`、`detail`、`ok`を持つ`Looked` |

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

ここでは長さ、チップセット、タイトルでダンプを識別することはなく、常にダイジェストで識別します。

### カートリッジのコードを読む

| モジュール | 呼び出し | 戻り値 |
|:--|:--|:--|
| [`commands.py`](commands.py) | `accesses(rom)` | `$8000`のデータポートまたは`$C000`のステータスポートへのすべての`Access`、バンク`$3F`のロング形式または絶対形式。それぞれ`offset`、`mnemonic`、`size`、`register`、`way`、`long`を持ちます |
| | `stores(rom)`、`store_at(rom, at)` | データポートへのストアのオフセットと、1つのオフセットにあるストア |
| | `read(rom, disassemble)` | ストアごとの`Site`、最大512バイトさかのぼってデコードしたもので、`command`、`narrow`、`issues`、`why`を持ちます |
| | `commands(sites)` | それらのサイトが発行するコマンドバイトをソートしたもの |
| [`sites.py`](sites.py) | `reached(rom)`、`census(rom)` | [snes-driver-python](https://github.com/gufranco/snes-driver-python)を通じて求めた、ロング形式がチップに到達する場所と、`sites`と`shapes`を持つ`Census` |

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

### 記録を読む

| モジュール | 呼び出し | 戻り値 |
|:--|:--|:--|
| [`exchanges.py`](exchanges.py) | `taken(trace)` | 発行したサイトで区切ったすべての`Exchange`。`site`、`command`、`words`、`answer`、そして答えが始まった後に書き込まれたワードを表す`later` |
| | `issuing(trace)` | データポートの下位半分にだけ書き込むプログラムカウンタと、それぞれの1つのコマンドバイト |
| | `census(trace)`、`read(path)` | `commands`、`total`、`issued(c)`、`distinct(c)`、`share(c)`、`sites(c)`、`table_bytes()`を持つ`Census` |
| | `spans(census, command)` | 引数の位置ごとの`Span`。`lowest`、`highest`、`distinct`、`width`、`bits`、そして異なる値が幅の半分以上を埋めるときの`dense` |
| | `readings(runs, command)` | キーが答えを決めるようになる引数を持つ、それ以前のコマンドを示す`Reading`。`carrier`、`rows`、`ambiguous`、`pure`、`tabulatable` |
| | `tier_of(command, distinct)` | `$00`には`computed`、16個までの引数セットには`inline`、それを超えると`table` |
| [`census.py`](census.py) | `taken(trace)`、`exchanges(trace)`、`report(census)` | 同じ問いをバイト列で区切ったもので、読み込みごとにやり取りが終わります。`$0a`はこの区切り方を壊します。ライブラリ専用で、ファイルを実行しても何も出力しません |

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

このトレースは、記録形式による3つの`$00`のやり取りです。`$00A000`のサイトはポートの下位半分に1バイトしか書き込まないので、これがコマンドサイトであり、その後の2ワードが引数です。`$0C4C`は`$1234`と`$5678`の、小数部15ビットの符号付き積で、これがチップの答えです。

### チップに問う

これらは[snes-dsp-python](https://github.com/gufranco/snes-dsp-python)を通じてマイクロコードを動かすため、いずれもマシン上にマイクロコードが必要です。

| モジュール | 呼び出し | 戻り値 |
|:--|:--|:--|
| [`tabulate.py`](tabulate.py) | `shape_of(command)`、`sweep(model="dsp1")` | `writes`、`reads`、`answers`を持つ`Shape`。チップが応答しなくなるまで1ワードずつ多く書き込んで測定します |
| | `ask(command, words, reads=1)`、`deterministic(command=0)` | 答えのバイトと、同一の2つの質問が同じ答えを返すかどうか |
| | `entries_for(words)`、`bytes_for(words, out=1)`、`storable(words)` | 入力全体にわたるテーブルの大きさと、それが96 Mbitカートリッジの半分に収まるかどうか。これらにマイクロコードは不要です |
| [`tables.py`](tables.py) | `KNOWN`、`carried(image)`、`find(words, table)`、`words(image)`、`table_bytes()` | 4つの`Table`レコード、イメージ内での各位置、そしてその大きさ。`words`は8,192バイトでないイメージに対して`WrongShape`を送出します |
| [`microcode.py`](microcode.py) | `program_of(mask)`、`dispatch(program)`、`handlers(program)`、`body(program, at)`、`listing(program)` | 2,048個のプログラムワード、各コマンドバイトの行き先、そしてハンドラからリターンまでの命令 |
| | `ISSUED` | カートリッジが書き込む19個のコマンドバイト |
| [`derived.py`](derived.py) | `reciprocal(part)`、`refined(part, value)`、`trig(part)`、`ask(part, command, words, answers)` | `$4000`から`$7FFF`までのチップの逆数と、すべての角度での正弦と余弦。`refined`は200命令の間にリターンしないと`Runaway`を送出します |
| | `leading(value)`、`counted()`、`doublings(folded)`、`inverted(mantissas, negative)` | 先頭ビットの数と、地面ルーチン用に索引を付け直した逆数。`inverted`は16,384エントリでないテーブルに対して`ValueError`を送出します |
| | `write(where, values)`、`write_bytes(where, raw)`、`pieces(where)` | 32,768バイトの断片の書き出しと読み戻し。`pieces`は断片が1つもないとき`FileNotFoundError`を送出します |
| [`complete.py`](complete.py) | `domains(runs)`、`wanted(values)`、`filled(command, keys, answers, have)` | `$13`と`$18`の各引数が取るすべての値、その全組み合わせ、そしてどの記録にもない組み合わせについてチップを動かして得た答え |
| [`routines.py`](routines.py) | `run(image, entry, words, answers)`、`asked(command, words, answers)`、`inputs(count, how_many, seed)` | 65816モデル上で実行したアセンブル済みルーチン1つ、同じ質問へのチップの答え、そしてシード付きの乱数引数。`run`は40,000命令を超えると`TooLong`を送出します |

### チップから読み取った演算

| モジュール | 呼び出し | 戻り値 |
|:--|:--|:--|
| [`attitude.py`](attitude.py) | `matrix(sine, cosine, five, six)` | `$02`が構築する行列の9つのセルを、`$5A`から`$7C`までのスクラッチアドレスをキーにしたもの |
| [`raster.py`](raster.py) | `answer(state, start, lines, table)`、`scanline(state, line, table)` | ラインごとの`$0a`の4つの答えワードを、チップと同じ方法で計算したもの |
| | `product`、`normalise`、`reciprocal`、`scaled`、`shortfall(got, want)` | 各段階と、2つの答えが何ライン一致するか |
| [`parameter.py`](parameter.py) | `GROUPS`、`CELLS`、`gathered(seen, slots)`、`fixed(runs)`、`mirrored(state)`、`sized(rows)` | 各状態ワードが`$02`の7つの引数のどれに従うか。`gathered`は1つのキーが2つの状態を与えると`Disagreement`を、`mirrored`は行列が2ワードの2回繰り返しでないと`NotMirrored`を送出します |
| [`state02.py`](state02.py) | `packed(table)`、`checked(table)`、`rows(table)`、`stride(table)` | キー付きテーブルをソート済みのリトルエンディアンワードにしたもの。`checked`は幅の異なる行に対して`Ragged`を、1ワードに収まらない値に対して`TooWide`を送出します |
| [`state02build.py`](state02build.py) | `gather(mask, where)`、`driven(part, sets)`、`tables(seen)`、`clamped(part)`、`checked(built)` | 3つの状態テーブルと、1つが32,768バイトのバンクを超えたときの`TooBig` |

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

`product`は小数部15ビットの符号付きワード2つを掛け合わせます。`normalise`はビット15とビット14が異なるまで左にシフトし、結果と並べてシフト回数を返します。`scaled`は指数を適用し、`$7FFF`でクランプします。行列は、5番目の引数については角度0で、6番目の引数については正弦と余弦がともに`$5A82`になる角度で構築しています。

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

行はキーでソートされているので、カートリッジは二分探索で行を見つけます。各行はキーワードの後に答えワードが続きます。

### テーブル、イメージ、パッチ

| モジュール | 呼び出し | 戻り値 |
|:--|:--|:--|
| [`lutbuild.py`](lutbuild.py) | `rows_of(runs)`、`completed(built, runs)`、`chosen(built, calls, room)`、`gather(where)` | コマンドごとの記録済みの答え。チップが状態を保持するものは`CARRIER`をキーにし、`$13`と`$18`は補完し、残りは1バイトあたりの呼び出し数で選びます |
| | `encode(tables)`、`sliced(raw)`、`banks(pieces, first)`、`source(pieces, first_bank)` | カートリッジが読む形のテーブルを、`$99`から始まり`$7E`と`$7F`を飛ばすバンクに分けたもの。`encode`は行が奇数バイトから始まる場合に`Uneven`を送出します |
| | `axes(built)`、`axes_source(found)` | キーがその値の全組み合わせであるコマンドと、探索せずにその行を数えるコード |
| | `CARRIER`、`COMPUTED`、`UNSTORABLE` | キャリア、演算で答えるコマンドである`$00`、`$04`、`$08`、`$80`、そして`$0a` |
| [`lut.py`](lut.py) | `KERNELS`、`expand(table, count)`、`blob(count)`、`cost(count)`、`image_bytes(count)` | 入力全体にわたって補間した4つのテーブルと、その大きさ |
| | `plan(census, command)`、`planned(census)`、`table(runs, command, carrier)`、`encode(table)` | 範囲または記録された集合を索引とするコマンドごとのテーブルと、そのエンコード |
| [`layout.py`](layout.py) | `runs(rom, least=256)`、`free(rom)`、`largest(rom)`、`fits(rom, wanted)`、`spread(rom, wanted)`、`must_grow(rom, wanted)` | `$FF`または`$00`の連なりを`(start, end)`として、その合計、最長のもの、そしてあるサイズが収まるかどうか |
| [`patch.py`](patch.py) | `plan(rom, limit)`、`applied`、`spanned`、`hooked`、`rearmed`、`held`、`hooked_nmi`、`redirected`、`declared`、`checksummed`、`symbols(path)` | コマンドが実行する各手順を、この順に。`held`は`$07E84`に必要な6バイトが空いていないと`ArmGapTaken`を、`hooked_nmi`は割り込みベクタが`$F0A0`を指していないと`VectorMoved`を送出します |

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

## 状況

何かを返すすべてのコマンドは、3つの記録に含まれるすべての質問について、チップが答えたとおりの答えを正確に返します。残る課題は速度で、[`OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md)で追跡しています。

| 部分 | 状態 |
|:--|:--|
| ダンプの識別、3地域すべて | [`artifacts.manifest.json`](artifacts.manifest.json)に対するSHA-256による |
| 各カートリッジがチップにアクセスする場所 | アクセスの両形式を、記録と照合済み |
| カートリッジが発行し得るコマンド | すべてのイメージで20個、記録と照合済み |
| チップが答える内容 | チップ自身のマイクロコードを実行 |
| 記録に含まれる引数セット | 3回の実行で73,341個 |
| チップが計算に使うテーブル | 4つ、1,280バイト、完全に再構築 |
| どの式でも再現できない3つのテーブル | チップから取得、294,912バイト |
| `$02`の状態、つまり`$0a`が読むすべて | チップから得た3つのテーブル、59,686バイト、6,980個すべての引数セットにわたって2つの答えを持つキーはなし |
| `$00`、`$08`、`$04` | 65816の演算、それぞれ400個の乱数引数セットでチップと完全一致 |
| 記録済みの答えのテーブル | 12コマンド |
| `$13`と`$18` | チップを動かして得た、定義域全体にわたって完全 |
| ルックアップ | 3地域すべてで、記録されたすべての質問について完全一致 |
| フォールバック | どの記録にもないキーを含め、すべてのコマンドにループせずに答えます |
| `$0a` | 65816、完全一致。3つすべての記録にわたる60個の引数セットで、43,440個中43,440個の答えワード |
| リダイレクトしたウィンドウを通るアクセス | 3バイトのアクセス200個をそれぞれ3バイトの呼び出しに置き換え、加えて5つの連なりを丸ごと置き換え |
| 読んだ値で演算するロングアクセス | 7個を経路変更、`adc`が6個と`eor`が1個 |
| ウィンドウのバンクを通るゲーム自身のワークRAM読み書き | 31個すべてを経路変更。[`OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md)の第30節 |
| デモ | 飛行し、地面を描画し、比較実行の終わりであるゲームフレーム405まで市販カートリッジの飛行を追従します。ワークRAMは1フレームあたり30から60バイト異なり、そのうち22バイトは毎フレーム異なり、さらにそのうち12バイトはゲームがワークRAMにコピーするパッチ済みの呼び出しです |
| 計器パネル | すべての画面で描画。デモを通じた画面の明るさのばらつきは0.05で、市販カートリッジと同じ水準。第32節 |
| 計器パネルを横切る帯 | 2.2%のフレームで発生。第48節 |
| `$02`が残す10ワード | 計算するか、キー全体を覆うテーブルから読み出し、デモ全体にわたる596フレームで10個すべてがチップと完全一致 |
| イメージサイズ | 拡大、ただしローカートリッジがアドレス指定できる範囲内 |

### 速度

| 測定項目 | 値 |
|:--|:--|
| `$0a`の1回の呼び出し、デモの149フレームでの平均 | 77,044プロセッササイクル |
| 最初ではない`$0a`の1回の呼び出し | 130,147サイクル、飛行中の24の状態にわたって3%以内で安定 |
| 距離が上のラインと一致し、答えをコピーするライン | 63.6% |
| 1ラインあたり6回のテーブル乗算が`$0a`に占める割合 | 54.7% |
| 4つの乗算テーブルの構築、フレーム外 | 62,665サイクル |
| 記録から得た600キーの1回のルックアップ | 1,566,405サイクル |
| 読み込みが8マスタークロックかかるときの1フレーム | 44,671プロセッササイクル |
| チップ、1回の呼び出しでゲームがブロックされた実時間 | 数十サイクルから約250、43回の呼び出しからなる中央値のフレームで約2,700 |
| `$00`、`$08`、`$04`の演算 | 398、920、833サイクル |

測定はプロセッサモデル上で行っており、実機では行っていません。変更を加えると測定ウィンドウが開いたときにデモがどこにいるかが変わるため、実機のフレームレート計は処理量に対して単調ではありません。地面に25,566サイクルの無駄な処理を加えたところ、より良いレートが表示されました。第36節から第39節、第49節、第51節、第52節に実行結果があります。

ゲームフレーム全体について、アセンブラの行マップに対するプログラムカウンタでサンプリングした結果です。

| 場所 | 割合 |
|:--|--:|
| 地面 | 46.8% |
| 記録済みの答えの探索 | 20.6% |
| ゲーム自身のコード | 15.4% |
| ポート | 11.2% |

探索を必要としない2つのコマンドは、[`lutbuild.py`](lutbuild.py)がその行を数えるコードとして出力します。そのうち1つはゲームフレームあたり9.4回問われます。第50節。

### テーブルがゲームのどれだけを覆うか

記録の一部から構築し、残りを問いました。

| 問うたもの | ヒット率 |
|:--|--:|
| 構築に使った質問 | 100% |
| 同じアトラクトデモの別の記録 | 93.4% |
| 前半を学習した記録の後半 | 11.2% |

3つの記録はすべて同じアトラクトシーケンスなので、中央の数値は繰り返しを測っています。最後の数値は、デモが一度もしなかったことをプレイヤーがしたときに遭遇するものです。この数値では`$10`のヒット率は10.9%、`$06`は0%です。`$06`はゲームが行うすべての呼び出しの31.7%を占めます。

`$13`と`$18`は外れることがないため、この方法では測っていません。これらの引数は量子化されています。`$13`のワードの1つは32,769の幅にわたり7つの値を取るため、幅で見積もると5.48e17行、値で見積もると1,512行になります。すべての組み合わせをチップを動かして得ており、記録に含まれる248行はすべて、同じ方法で動かしたときに同一の結果になりました。

`$10`の定義域は4,996通りの組み合わせで、補完していません。キーだけで動かすと100回中83回記録を再現するため、埋めた行の17%は誤りになります。欠けた行はコードにフォールバックしますが、誤った行はフォールバックしません。

### ルックアップが答える内容

プロセッサモデル上で3つの記録に対して、地域ごと、コマンドごとに40個の質問で動かしました。

| コマンド | 正解 | 誤答 |
|:--|--:|--:|
| `$00` `$02` `$03` `$06` `$08` `$0c` `$0d` `$0e` `$10` `$13` `$14` `$1b` `$28` | 各120 | 0 |
| `$04` | 40 | 0 |
| `$18` | 10 | 0 |

`$04`と`$18`は、記録に含まれる異なる質問の数がより少なくなっています。

## 測定したこと

### 1つの置き換えで3地域すべてを覆う

カートリッジが使う両方の形式で、データポートへのストアをコードから読むと、USAイメージで208個、日本版で218個、欧州版で208個になります。そこから読み取った20個のコマンドバイトは、3つすべてで同じ20個です。

ロング形式はどの地域でも2つのアドレスに到達します。`$3f:8000`への84命令と`$3f:c000`への9命令で、3つすべてで同じ数です。同じドライバが3回現れているだけなので、1地域の置き換えは残り2地域の置き換えにもなります。

### ドライバの大部分はロング形式の探索からは見えない

ホットパスは`pea $003f`と`plb`で一度だけデータバンクを設定し、その後は2バイトで表記されバンクを指定しない絶対形式のストアを使います。すべてのアクセスのプログラムカウンタを持つ日本版イメージの記録に対して測定した結果です。

| | 命令 | ロング形式 | 絶対形式 | ロング形式で移動したバイトの割合 |
|:--|--:|--:|--:|--:|
| チップへの書き込み | 118 | 40 | 78 | 62.2% |
| チップからの読み込み | 47 | 13 | 34 | 7.9% |

[`commands.py`](commands.py)は両方を読みます。ゲームで最もホットなループは`plb`の後の`sta $8000`で、その後にポーリングと読み込みが176回続きます。

エンコーディングによる探索では、命令ではないバイトも報告されます。USAイメージでは、122個のロング形式の一致のうち29個が、バンク`$30`から`$3e`にわたる29の異なるアドレスに1つずつあります。日本版では28個、欧州版では30個で、これが3つの合計の差のすべてです。

### 各コマンドが読むワード数

チップのプロトコルを通じて測定しました。必要な数より1ワード少なく書き込んだコマンドはまだエコーを返し、1ワード多く書き込むと応答しなくなります。その沈黙から1つ戻った数が、そのワード数です。これは演算で確認しています。コマンド`$00`は2つのワードの小数部15ビットの符号付き積を答え、`0x1234 x 0x5678 -> 0x0C4C`となります。

256個のコマンドバイトのうち、何らかの答えを返すのは45個です。

| 入力ワード | 出力ワード | コマンド | すべての答えのテーブル |
|--:|--:|--:|:--|
| 1 | 1 | 2 | 131,072バイト、収まります |
| 2 | 1 | 2 | 8,589,934,592バイト、96 Mbitイメージの683倍 |
| 3 | 1 | 14 | 562 TB |
| 4 | 1 | 7 | さらに大きい |
| 5 | 1 | 17 | さらに大きい |
| 6 | 12 | 1 | さらに大きい |
| 10 | 1 | 2 | さらに大きい |

すべての答えを保存できるコマンドは2つです。残る43個のうち最小のものでも、96 Mbitイメージの683倍です。上の表はチップの入力定義域の大きさを示しています。ゲームが問うものははるかに小さく、以下の節でその大きさを示します。

### ゲームが問うもの

日本版イメージを入力なしで12,000フレーム実行し、アトラクトデモを飛行させたところ、30のサイトから257,189個のコマンドが発行されました。NTSCイメージはフレーム10,418以降チップにアクセスしなくなり、PAL版は11,999でもまだ飛行しています。欧州版が`$04`を発行し、他の2つが一度も発行しないのはこのためです。

| コマンド | 割合 | 発行数 | サイト | 内容 |
|:--|--:|--:|--:|:--|
| `$06` | 28.9% | 74,261 | 2 | |
| `$13` | 25.4% | 65,332 | 1 | |
| `$00` | 15.0% | 38,668 | 10 | 符号付き乗算、計算で対応 |
| `$11` | 4.7% | 12,136 | 2 | |
| `$0a` | 2.7% | 6,946 | 1 | 176回読まれるストリームで答えます |
| その他13個 | 23.3% | 59,846 | 14 | |

### 発行したサイトで記録を区切る

`$0a`はカートリッジが176回読むストリームで答え、チップはそのストリームの間も書き込みを受け付けます。すると1つのやり取りの中の読み込みがその終わりのように見え、そのように区切ると、連なりの10分の1が32バイト以上離れたコードからの書き込みを含みます。

[`exchanges.py`](exchanges.py)は代わりにコマンドサイトで区切ります。データポートの下位半分にしか触れないプログラムカウンタはコマンドを発行したもので、両方の半分に触れるものは引数ワードを書き込んだものです。

3回の実行全体で、19個のコマンドにわたる73,341個の異なる引数セットがあり、1つの答えを保存すると586,728バイトになります。

| | コマンド | 行 | バイト | トラフィックの割合 |
|:--|--:|--:|--:|--:|
| インラインの比較チェーン | 5 | 22 | 176 | 30.5% |
| テーブル | 13 | 46,832 | 374,656 | 54.3% |
| 計算、乗算であるため | 1 | なし | 0 | 15.8% |

### チップが計算に使うもの

uPD77C25は、プログラムの横に1024ワードのデータROMを持っています。[`tables.py`](tables.py)は各候補を式から再構築して探索します。4つがワード単位で一致して見つかります。

| テーブル | ワード | 式 | バイト |
|:--|--:|:--|--:|
| 逆数 | 128 | `2^22 / (128 + k)`、丸めてクランプ | 256 |
| 正弦 | 128 | `sin(pi k / 128) x 32768`、小数部は切り捨て | 256 |
| 余弦 | 128 | `cos(pi k / 128) x 32768`、小数部は切り捨て | 256 |
| 逆余弦 | 256 | `acos(k / 256) x 32768 / pi` | 512 |
| | | **合計** | **1,280** |

平方根も逆正接もありません。両方のマスクが同じ4つを持ち、DSP-1Bはそのうち3つを2ワード下に置いています。

### 各引数が取る範囲

[`exchanges.py`](exchanges.py)は、各引数位置での最小値、最大値、異なる値の数を報告します。

| 位置の様子 | コマンド | テーブルの索引 |
|:--|--:|:--|
| 1つまたは少数の値 | 5 | 値、インライン |
| 数千個で、範囲を埋めている | 2 | 範囲、2^18行と2^20行 |
| 少なくとも1つがワード全体にわたる | 12 | 密なものはなし |

コマンド`$0d`は3つの位置それぞれで約4千個の異なる値を取り、それぞれが0から65,535の全範囲にわたります。範囲によるテーブルは2^48行になり、そのほとんどは誰も送らない入力のためのものなので、両方の数値を常に併記しています。

### チップは状態を保持する

答えを返す16個のコマンドのうち7個は、同一の引数に対して異なる答えを返します。別のコマンドが読み込んだ行列を読むコマンドは、自身の引数だけの関数ではないためです。`$0e`はすべての記録で1つの引数セットを取り、それに6,260通りの答えを返します。

7個のうち6個は、キーにそれ以前の1つのコマンドの引数も含めると決定的になります。これが[`lutbuild.py`](lutbuild.py)の`CARRIER`です。

| コマンド | 自身の引数と直前のもので索引 |
|:--|:--|
| `$03` | `$14` |
| `$06`、`$0d`、`$0e` | `$02` |
| `$13`、`$1b` | `$11` |

`$0a`が7個目です。それ以前のどのコマンドも、単独でも、2つや3つの組み合わせでも、これを決定しません。異なる答え全体をそれぞれ保存すると16,762,160バイトかかり、4ワードの各ステップを保存すると索引の前に538,583個の異なるステップが必要です。そのため計算で対応しています。1ラインあたり1回の正規化、1回の逆数、2回の乗算、2回のシフトで、チップのプログラムから段階ごとに読み取り、そのレジスタと照合しています。第22節。

### テーブルのエンコード結果

[`lutbuild.py`](lutbuild.py)は各コマンドの行をキーでソートするので、カートリッジは二分探索で行を見つけます。3つの記録から、`$13`と`$18`を補完する前の値です。

| コマンド | 索引 | 行 | キーワード | 答えワード | バイト |
|:--|:--|--:|--:|--:|--:|
| `$06` | 引数と直前の`$02` | 75,278 | 10 | 3 | 1,957,228 |
| `$0d` | 引数と直前の`$02` | 6,557 | 10 | 3 | 170,482 |
| `$02` | 引数 | 6,980 | 7 | 4 | 153,560 |
| `$0e` | 引数と直前の`$02` | 6,980 | 9 | 2 | 153,560 |
| `$03` | 引数と直前の`$14` | 5,268 | 9 | 3 | 126,432 |
| `$14` | 引数 | 4,406 | 6 | 3 | 79,308 |
| `$28` | 引数 | 6,182 | 3 | 1 | 49,456 |
| `$1b` | 引数と直前の`$11` | 2,986 | 7 | 1 | 47,776 |
| `$0c` | 引数 | 3,480 | 3 | 2 | 34,800 |
| `$10` | 引数 | 2,498 | 2 | 2 | 19,984 |
| `$13` | 引数と直前の`$11` | 244 | 7 | 3 | 4,880 |
| `$18` | 引数 | 4 | 4 | 1 | 40 |
| | | | | **合計** | **2,797,956** |

これは32,768バイトのバンク86個分です。行は答えだけでなくキーも持ち、チップが状態を保持するため、`$06`は3ワードの答えに10ワードのキーを費やしています。

### 記録が言えることと言えないこと

記録はゲームが何をしたかを示すだけで、何ができるかは示しません。ほとんどの引数は機体の姿勢から得られ、ほぼ毎フレーム新しい値を取るため、入力集合が閉じていることを示す記録はありません。そのため、すべてのコマンドはテーブルの背後にコードによるフォールバックを持っています。

残る半分はコードを読むことで答えられます。[`commands.py`](commands.py)はすべてのイメージから20個のコマンドバイトを読み取り、欧州版ではさらに1つ、`$80`を読み取ります。日本版の記録に対しては、実行された30サイトのうち27で一致し、矛盾はなく、3つについては何も言えません。欧州版の記録に対しては36のうち33で一致し、矛盾はありません。

| | コマンド |
|:--|--:|
| コードから読み取ったもの、3イメージすべて | 20 |
| 欧州版がさらに読むもの | `$80` |
| 日本版の記録が発行したもの | 18 |
| 欧州版の記録が発行したもの | 19 |
| 読み取ったが実行は一度も確認されないもの | `$21`、`$23` |

`$80`はチップをコマンド待ちの状態に戻します。カートリッジは`$0702a`でこれを128回続けて書き込み、チップをフラッシュします。

### 市販イメージの空き

[`layout.py`](layout.py)は、同じバイトが256バイト以上繰り返す連なりを測定します。

| 地域 | その連なりの空き | 最大の単一の連なり |
|:--|--:|--:|
| USA | 63,122 | 4,249 |
| Japan | 74,207 | 8,395 |
| Europe | 63,122 | 4,249 |

いずれも1,280バイトの4つのテーブルを1か所に収められます。記録済みの答えのテーブルは収まらないため、イメージを拡大します。同じバイトの繰り返しは何も使っていないことの証拠なので、候補となる連なりは、何かを置く前にドライバの全数調査と照合します。

<a id="the-dumps"></a>

## ダンプ

No-Introでの名前に従っています。どのダイジェストもコピアヘッダのないファイル全体に対するものです。SHA-256で判定し、CRC32は今もそれをキーにしているデータベースとの照合用に載せています。

| ファイル | 読み込み先 | サイズ |
|:--|:--|--:|
| Pilotwings、USA | `external/roms/pilotwings-usa.sfc` | 524,288 |
| Pilotwings、Japan | `external/roms/pilotwings-jp.sfc` | 524,288 |
| Pilotwings、Europe | `external/roms/pilotwings-eur.sfc` | 524,288 |

| 地域 | SHA-256 | CRC32 |
|:--|:--|:--|
| USA | `03d0127f5de3237e22ad00de0c20763274da7b71142dde693240ac96d10983a3` | `266C44ED` |
| Japan | `d1845de22c3c7f2606bda20e09c8f7a78f92f5cbbb6bfe01f96a1d1e84b30394` | `77871727` |
| Europe | `f70a72f3d3a65497cdc4d849877a29cf4f7bd10439bb7f5cb8675cdfc0e706d4` | `DEF45776` |

3つすべてがバージョン`0x00`を宣言しています。このゲームをもとにしたNintendo Campus Challengeのカートリッジは同じ524,288バイトで、同じチップセット`0x03`を宣言し、同じ内部タイトル`PILOTWINGS`を持ちます。それを区別できるのはマップバイトとダイジェストだけで、識別をダイジェストのみで行うのはこのためです。

## その下にあるモデル

| モデル | サブモジュール | 検証の基準 |
|:--|:--|:--|
| 65816 | [mos65xx-python](https://github.com/gufranco/mos65xx-python) | オペコードごとのスイート、5,120,000ケース |
| DSP-1 | [snes-dsp-python](https://github.com/gufranco/snes-dsp-python) | チップ自身のマイクロコードを実行 |
| カートリッジのマップ | [snes-mapper-python](https://github.com/gufranco/snes-mapper-python) | 実際のカートリッジのライブラリにあるすべてのヘッダの組み合わせ |
| ROMイメージ | [snes-rom-image-python](https://github.com/gufranco/snes-rom-image-python) | 同じライブラリを書き直して確認 |
| ドライバ | [snes-driver-python](https://github.com/gufranco/snes-driver-python) | カートリッジのコードがコプロセッサにアクセスする場所 |

グラフィックスのモデルはありません。このチップは数値を計算するだけで、タイルには一切触れません。

上のすべてのサイクル数は65816モデルという計測器から得ています。バスを1サイクルずつ駆動するので、ルーチンのコストはかかったサイクルそのものです。メモリとレジスタはゼロではなく再現可能なスクランブル値で始まるため、一度も書き込まれていないものを読むと誤った答えとして現れます。

## カートリッジ内の配置

ローカートリッジはバンク`$00`から`$7D`を持ちます。このプロジェクトが追加するものはすべて`$80`以降のミラーを通じて読みます。ミラーは、`$420D`を設定すると、8マスタークロックの代わりに6マスタークロックで読み込みに応答します。

| 内容 | バンク | 読み込み経路 |
|:--|:--|:--|
| 出荷時のゲーム | `$00`-`$0F` | |
| 置き換えのコード | `$10` | `$90` |
| チップから取得した正弦と余弦 | `$11`-`$18` | `$91`-`$98` |
| 記録済みの答え | `$19`-`$6F` | `$99`-`$EF` |
| `$0a`が読む`$02`の状態 | `$70`-`$72` | `$F0`-`$F2` |
| チップから取得した逆数 | `$73` | `$F3` |
| ゲームのリダイレクトされたアクセスが着地するウィンドウ | `$7D` | `$7D` |

記録された12個のコマンドすべてに答えるには87バンクが必要で、そのうち60バンクは`$06`用です。忠実度、安定性、速度のいずれかが得られる場合、イメージは96 Mbitまで拡大して構いません。`$7D`を超えるバンクにはウィンドウ方式のレイアウトが必要なので、可能な限りイメージはその下に収めています。2 MiBと4 MiBのイメージは、ヘッダのサイズバイトが一致すれば同じように起動してデモを実行します。[`patch.py`](patch.py)はイメージの長さからそのバイトを設定します。

## 正しいか

オラクルは2つあり、ここにあるものがDSP-1の結果を独自に計算することはありません。何が問われるかは市販カートリッジが決めます。コマンドと引数セットが質問になるのは、市販カートリッジがそれを送るからです。答えはチップのマイクロコードが決め、[snes-dsp-python](https://github.com/gufranco/snes-dsp-python)を通じて実行します。

| 主張 | 検証の基準 | 場所 |
|:--|:--|:--|
| ダンプがそのダンプであること | [`artifacts.manifest.json`](artifacts.manifest.json)のSHA-256 | [`tools/identify.py`](tools/identify.py) |
| カートリッジがチップにアクセスする場所 | コードの読み取りを実行の記録と双方向に照合 | [`commands.retail.test.py`](commands.retail.test.py)、[`sites.retail.test.py`](sites.retail.test.py) |
| ルーチンが答える内容 | 同じ質問をチップに問うた結果 | [`routines.retail.test.py`](routines.retail.test.py)、[`raster.retail.test.py`](raster.retail.test.py)、[`attitude.retail.test.py`](attitude.retail.test.py) |
| 4つのテーブル | マイクロコードのデータROM、ワード単位 | [`tables.retail.test.py`](tables.retail.test.py) |
| パッチ | 市販イメージ | [`patch.retail.test.py`](patch.retail.test.py) |

ダンプまたはマイクロコードを必要とするチェックは、10個の`*.retail.test.py`ファイルにある87件のテストで、どちらかがないとスキップされたと報告します。アーティファクトのあるマシンとないマシンでは実行されるパスが異なるため、これらはカバレッジの測定から除外しています。

このプロジェクトはDSP-1を再現し、DSP-1Bは再現しません。アトラクトデモはボタン入力の記録であり、DSP-1Bの修正された演算では、同じ入力で機体が地面に突っ込みます。市販基板がどちらのマスクを搭載しているかはダンプからは読み取れません。この問いと、見かけより狭い他のすべての主張は、それを決着させる測定とともに[`OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md)にあります。

## 開発に参加する

| 必要なもの | 場所 |
|:--|:--|
| すべてのゲートとその実行順序 | [CONTRIBUTING.md](CONTRIBUTING.md) |
| コーディングエージェント向けの同じ内容 | [AGENTS.md](AGENTS.md) |
| このリポジトリがファミリーの他のリポジトリと共有する標準 | [FAMILY.md](FAMILY.md) |
| バグ報告 | [GitHub Issues](https://github.com/gufranco/snes-pilotwings-nochip/issues) |
| セキュリティ報告 | [SECURITY.md](SECURITY.md) |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 mypy .
for t in *.test.py tools/*.test.py; do python3 "$t" || break; done
python3 -m coverage erase
for t in *.test.py tools/*.test.py; do python3 -m coverage run -a "$t"; done
python3 -m coverage report
```

41ファイルにわたる1,055件のテストがあり、各モジュールの横に`<module>.test.py`が1つずつあります。カバレッジは命令と分岐の100%を必須のゲートとし、[`pyproject.toml`](pyproject.toml)で設定しています。コミットはConventional Commitsに従い、semantic-releaseがそこからバージョンを決定します。

コメントはアセンブリにのみ書きます。内容は入口と出口の状態、レジスタ幅、各アドレスの由来です。Pythonのソースにはコメントがありません。

カートリッジやマイクロコードのイメージをIssueに添付しないでください。また、どちらかをダウンロードできる場所へのリンクも貼らないでください。ダイジェストはファイルを含まずにそれを識別します。

## 参考文献

- No-Intro、3つの市販ダンプの名前とダイジェストについて。
- コミット`2971061cf07fdc6fc7d18883edf4e648eb16a6d2`のsnes9x、https://github.com/snes9xgit/snes9x 。すべてのポートアクセスを記録するために[`emu/Dockerfile`](emu/Dockerfile)でビルドしています。記録はそのエミュレータのDSP-1についての証拠であるため、ルックアップは記録ではなくチップ自身のマイクロコードと照合しています。
- asar v1.81、https://github.com/RPGHacker/asar 。[`asm/Dockerfile`](asm/Dockerfile)でビルドしています。
- nevikstiによるチップなしのStar Ocean変換、ローカートリッジのアドレス空間より大きいイメージのアドレス指定規則について。
- Nintendo EADとArgonaut、ゲームについて。

## 引用

[CITATION.cff](CITATION.cff)は、[`version.py`](version.py)にバージョンを刻むスクリプトである[`scripts/set-version.sh`](scripts/set-version.sh)によって、リリースごとに更新されます。

## ライセンス

MITです。[LICENSE](LICENSE)を参照してください。ツール群、アセンブリ、この文書に適用され、ゲームについての権利は一切付与しません。ここではROMデータを一切配布していません。すべてはご自身が用意したダンプに対して動作します。
