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
assets/audio/           旋律示範音檔（由工具自動產生）
tools/make-audio.js     由 chorusMelody 合成 wav
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

## 本機預覽

```bash
python3 -m http.server 8000
# 開 http://localhost:8000
```
