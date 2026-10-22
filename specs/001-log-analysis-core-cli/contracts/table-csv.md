# Contract: 表 CSV（出力形式と書式）

コマンドラインの出力、正解生成プログラム（`tools/mfc_golden`）の出力、`tests/data/**/golden/*.csv` は、すべてこの形式に従う。
同じログからは、Python 版と正解生成プログラムで**バイト単位で同じファイル**ができなければならない。

## ファイル形式

- 文字コード UTF-8（BOM なし）、改行 LF、最後の行にも LF を付ける。
- 区切りは `,`。引用符は使わない。セルに `,`・`"`・CR・LF が入るときは書き出さずにエラーにする。
- 行の構成:

| 行 | 内容 |
|---|---|
| 1 | 表題（1 セル） |
| 2 | 注記。バス負荷は要約（1 セル） |
| 3 | 列見出し |
| 4 以降 | 表の行（0 行のこともある） |

- 標準出力に複数の表を出すときは、表の間に空行を 1 行入れる。順は latency、busload、txwait、jitter。
- ファイルに出すときの名前は `latency.csv`、`busload.csv`、`txwait.csv`、`jitter.csv`。

## 文言（MFC `MFCApplication1.rc` の文字列テーブルからそのまま）

`<P>` はプロジェクト名（.canprj のファイル名、拡張子付き）、`<N>` は OVERWRITE の行数（`%d`）。

| kind | 表題 | 2 行目 | 列見出し |
|---|---|---|---|
| latency | `受信完了時間 - <P>` | `送信要求 → 受信完了の時間（再送は届いた 1 回を 1 件）。破棄（OVERWRITE）<N> 件は含みません。` | `送信 ECU,受信 ECU,件数,最小 (µs),平均 (µs),最大 (µs),95% (µs)` |
| busload | `CAN バス負荷 - <P>` | 要約（下記） | `ECU,送信フレーム数,使用率 (%)` |
| txwait | `送信待ち時間 - <P>` | `送信要求 → 送信開始の時間（送信 1 回を 1 件。再送は送れた 1 回）。破棄（OVERWRITE）<N> 件は含みません。` | `CAN ID,送信 ECU,件数,最小 (µs),平均 (µs),最大 (µs),95% (µs)` |
| jitter | `送信ジッター - <P>` | `連続する送信開始の間隔 − 送信要求の間隔（正は遅れ、負は早まり）。標準偏差は件数で割った値です。` | `CAN ID,送信 ECU,周期 (ms),件数,最小 (µs),最大 (µs),標準偏差 (µs)` |

- バス負荷の要約: `平均負荷 <A>%　最大負荷 <M>%（<S>〜<E> ms）　範囲 0〜<R> ms（10 ms ごと）`
  （`　` は全角スペース U+3000。IDS_BUS_SUMMARY の `%%` は `%` 1 文字になる）
  - A = Fixed1(average_pct)、M = Fixed1(max_pct)、S = max_section × 10、E = (max_section + 1) × 10、R = range_us / 1000（整数除算）
- 文字は .rc のとおり: µ は U+00B5、→ は U+2192、− は U+2212、〜 は U+301C、括弧は全角（`（` `）`）、列見出しの `(µs)` は半角括弧。
  実装では .rc から文字列をコピーし、目で打ち直さない。

## セルの書式（`reference/mfc/AnalysisDlg.cpp` と同じ書式文字列）

| 名前 | 書式 | 使う所 |
|---|---|---|
| EcuName(n) | `ECU %02d` | 送信 ECU、受信 ECU、ECU |
| CanIdText(id) | `0x%03X` | CAN ID |
| 整数 | `%lld` | 件数、最小、最大、95%、送信フレーム数 |
| Fixed1(x) | `%.1f` | 平均、標準偏差、使用率、要約の % |
| 周期 | `period_us % 1000 == 0` なら `%lld`（period_us / 1000）、それ以外は `%.3f`（period_us / 1000.0） | 周期 (ms)。剰余と除算は C++ と同じく 0 方向（research R-4） |

## 行の作り方

### latency（`CLatencyDlg::CreateContent`）

- 行 i = 0（全体）: `全体`, ``, count, min, Fixed1(mean), max, p95
- 行 i ≥ 1: EcuName(tx), EcuName(rx), count, min, Fixed1(mean), max, p95

### txwait（`CTxWaitDlg::CreateContent`）

- 全体の行: `全体`, ``, count, min, Fixed1(mean), max, p95
- ほかの行: CanIdText(id), EcuName(tx), count, min, Fixed1(mean), max, p95

### jitter（`CJitterDlg::CreateContent`）

- count > 0: CanIdText(id), EcuName(tx), 周期, count, min, max, Fixed1(std_dev)
- count = 0: CanIdText(id), EcuName(tx), ``, `0`, ``, ``, ``

### busload（`CBusLoadDlg::CreateContent`）

- 各 ECU: EcuName(node), frame_count, Fixed1(usage_pct)

## 例（AS-001 の 3 行ログ、プロジェクト名 `as001.canprj`）

`txwait.csv`:

```text
送信待ち時間 - as001.canprj
送信要求 → 送信開始の時間（送信 1 回を 1 件。再送は送れた 1 回）。破棄（OVERWRITE）0 件は含みません。
CAN ID,送信 ECU,件数,最小 (µs),平均 (µs),最大 (µs),95% (µs)
全体,,2,0,126.0,252,252
0x080,ECU 03,1,0,0.0,0,0
0x100,ECU 01,1,252,252.0,252,252
```

`latency.csv`:

```text
受信完了時間 - as001.canprj
送信要求 → 受信完了の時間（再送は届いた 1 回を 1 件）。破棄（OVERWRITE）0 件は含みません。
送信 ECU,受信 ECU,件数,最小 (µs),平均 (µs),最大 (µs),95% (µs)
全体,,3,246,330.0,498,498
ECU 01,ECU 05,1,498,498.0,498,498
ECU 03,ECU 01,1,246,246.0,246,246
ECU 03,ECU 05,1,246,246.0,246,246
```
