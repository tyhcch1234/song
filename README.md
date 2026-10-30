# 歌 · 廣東話原創

廣東話原創歌詞集，一個持續累積嘅作品庫。

**網站**：https://tyhcch1234.github.io/song/

## 目前作品

| No. | 歌名 | 主題 | 日期 |
|-----|------|------|------|
| 01 | 濃煙裡的手 | 消防員 · 致敬 | 2026-10-30 |

## 專案結構

```
index.html              頁面外殼
assets/style.css        樣式
assets/app.js           列表 / 歌曲頁渲染 + 播放器
assets/songs.js         ★ 所有歌曲資料（唯一需要手改嘅檔）
assets/audio/           旋律示範 + 唱歌版音檔（由工具自動產生）
tools/make-audio.js     由 chorusMelody 合成旋律 wav
tools/sing.py           合成唱歌版（共振峰包絡 + 諧波激勵）
```

## 新增一首歌

只需要喺 `assets/songs.js` 嘅 `window.SONGS` 陣列最前面加一個物件，網站會自動更新列表同路由：

```js
{
  id: "my-new-song",          // 英文小寫加連字號，會成為網址 #/s/my-new-song
  no: 2,                      // 編號，遞增
  title: "歌名",
  subtitle: "English Title",  // 可選
  dedication: "一句獻詞。",
  date: "2026-11-05",
  tags: ["主題", "情緒"],
  meta: { key: "G 大調", bpm: 84, meter: "4/4", style: "廣東流行", length: "約 3:50" },
  sections: [
    { name: "主歌一", en: "Verse 1", chords: "G — D — Em — C", lines: ["第一句", "第二句"] }
  ],
  chorusMelody: {             // 可選：有嘅話會出現簡譜試聽器
    label: "副歌旋律示範",
    note: "說明文字",
    notes: [
      { s: "歌", n: "G4", d: 0.5, line: 1 }   // s=字, n=音高, d=拍數, line=第幾行
    ]
  },
  notes: ["創作筆記..."]       // 可選
}
```

`n` 用科學音名（`C4`、`G4`、`A4`、`C5`…），`d` 係拍數（0.5 = 八分音符，1 = 四分音符）。簡譜數字由音名自動換算，唔需要另外手打。

## 旋律音檔

寫好 `chorusMelody` 之後行一次：

```bash
node tools/make-audio.js            # 全部
node tools/make-audio.js my-new-song  # 指定一首
```

會按 `meta.bpm` 同拍數合成 `assets/audio/<id>-chorus.wav`（22050 Hz、單聲道、16-bit，約 1 MB/首）。
播放器會自動用呢個路徑；**檔案唔存在或者載入失敗，會自動退回瀏覽器即時合成**，唔會靜靜地冇聲。

用 wav 而唔用 mp3，係因為唔想 build 流程依賴 ffmpeg／lame 等外部程式——任何電腦 `node` 一行就出到，且所有瀏覽器（包括 iOS Safari）原生支援。

> 手機聽唔到聲，通常係側邊嘅**靜音掣**或者媒體音量。用 `<audio>` 播檔案走媒體聲道，唔受靜音掣影響；之前用 Web Audio 即時合成就會被靜音掣完全靜音，所以已經換走。

## 唱歌版（合成人聲）

```bash
python3 tools/sing.py                # 全部有 chorusMelody 嘅歌
python3 tools/sing.py hand-in-smoke  # 指定一首
VOCAL_OCTAVE=-1 python3 tools/sing.py  # 想降八度唱（預設用記譜音域 C4–C5）
STEM=/tmp/stem.wav python3 tools/sing.py  # 另存人聲乾軌，方便驗證
```

做法（唔用外部模型，純 numpy/scipy）：

1. 逐個字用 `zh-HK-HiuMaanNeural` 發音，裁走前後靜音
2. 逐幀自相關搵有聲段，對母音段做平均幅度譜 + 倒頻譜 lifter → **共振峰包絡**
3. 用目標音高生成諧波，幅度喺包絡上按 `k×f0` 取樣 → **音高精準、共振峰唔會被拉高**（前兩版用變速變調整段音，所以似讀字）
4. 音頭 70ms 由前一個音 glide 過去、長音加 5.2 Hz 顫音、聲母段保留原音
5. 疊和弦 pad + 琶音 + bass + 底鼓，一小節前奏，卷積 reverb

輸出 `assets/audio/<id>-vocal.wav`（約 29 秒，含前奏）。

實測：**46 個音全部誤差 ≤0.1%**；母音頻譜包絡同原音相關 0.845，共振峰位置一致（例：280/680/1120 Hz 前後不變）。

> 限制：呢個係「頻譜包絡 + 諧波」嘅歌聲合成，會似 vocoder／舊式歌聲合成器，唔會似 Suno 或真人。強項係音高、拍子、歌詞準，適合試旋律、試速度、試 key、做 demo 底。要真·唱歌質感，用 `prompts/` 入面嘅 Suno 提示包生成，再放返 `assets/audio/`。

## 本機預覽

```bash
python3 -m http.server 8000
# 開 http://localhost:8000
```
