# 正解 CSV の目視確認記録（spec FR-040e）

`tools/mfc_golden` で作ったこのフォルダの正解 CSV のうち 1 画面分を、MFC 版の解析画面と目で見比べた記録。
手順は [tools/mfc_golden/README.md](../../../../tools/mfc_golden/README.md) の「目視確認」。

| 項目 | 内容 |
|---|---|
| 確認日 | 2026-10-22 |
| 確認者 | I.H（MFC 版で画面を開き、スクリーンショット 2 枚を撮影。セルの照合は Claude Code が `txwait.csv` と 1 セルずつ行い、I.Hが結果を確認） |
| 確認した画面 | 送信待ち時間（ウィンドウタイトル「送信待ち時間 - sample_vehicle_16ecu.canprj」）→ `txwait.csv` |
| MFC 版のビルド | `C:\work\claude\can_simulator` の `66fc62e`（`git rev-parse --short HEAD`。2026-10-21「TRACE のメッセージを英語にする（CI の C4566 対策）」、作業ツリーに未コミットの変更なし） |
| 結果 | **一致**。表題、注記（破棄（OVERWRITE）0 件）、列見出し 7 列、表の全 32 行（全体＋CAN ID 31 行。1 枚目で全体〜0x200、2 枚目で 0x120〜0x408）の全セルが `txwait.csv` と一致。不一致なし |

> 送信 ECU は ECU 01〜ECU 16 の 16 台で、プロジェクト（16 ECU）と矛盾しないことも確認した。
