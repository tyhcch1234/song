# 《濃煙裡的手》— Suno 生成用提示包

呢個檔案係為 Suno（或同類端到端音樂生成模型）準備嘅輸入。分兩格填：**Style** 同 **Lyrics**，再填 Title。

---

## Title

```
濃煙裡的手
```

## Style of Music（直接貼）

```
Cantonese pop ballad, male lead vocal, 76 BPM, 4/4, C major,
intimate piano intro, warm string pad, soft brush drums entering on verse 2,
restrained verse, wide emotional chorus, subtle guitar arpeggio,
cinematic build in bridge, key change up a whole step on final chorus,
natural Cantonese diction, breathy sincere delivery, analogue warmth, wide stereo mix
```

想再收窄，可以加 `Exclude styles`：

```
EDM, rap, autotune, heavy distortion, female vocal, mandarin pronunciation
```

## Lyrics（直接貼，連方括號標籤）

```
[Intro]
(piano, 4 bars)

[Verse 1]
凌晨三點 鐘聲一響
鞋都未着好 就跳上車廂
街燈向後退 我望住窗外
唔係唔驚 只怕慢咗一秒

[Pre-Chorus]
手機入面 老婆留咗句
「記得食飯 記得返嚟」
我冇時間覆 只係望一望
然後戴上面罩 走入呢片灰

[Chorus]
濃煙裡面 我伸手搵你
睇唔到路 都要行前多一呎
如果呢個城市 仲有人等緊返屋企
就算熏到眼痛 都唔會放開你

你唔使驚 我跟住你背脊
一步一步 我哋行返出去
如果呢個城市 仲有人肯為人留低
我呢條命 就唔算白過一日

[Verse 2]
十八樓 走廊已經塌咗
條水喉扯到盡 手心都震
有個細路 攬實我隻腳
佢話：「叔叔，我媽媽仲喺裡面。」

[Pre-Chorus]
我冇講嘢 只係點一點頭
抱起佢 交俾下一個兄弟
轉身再入去 熱到面罩都溶
但我記得 佢媽媽對眼

[Chorus]
濃煙裡面 我伸手搵你
睇唔到路 都要行前多一呎
如果呢個城市 仲有人等緊返屋企
就算熏到眼痛 都唔會放開你

[Bridge]
唔係想做英雄
只係有人要救
每次行入去
都可能冇得行返出嚟
但有一句 我哋冇寫喺牆上
先救人 後講自己

[Chorus]
濃煙裡面 我伸手搵你
睇唔到路 都要行前多一呎
如果呢個城市 仲有人等緊返屋企
就算熏到眼痛 都唔會放開你

[Outro]
天光嘅時候 火已經熄
我坐喺路邊 除低頂帽
有人遞支水 講聲「多謝你」
我笑一笑 話：「呢啲係我哋嘅工作。」
然後望住個天 等下一次鐘聲
(piano out)
```

## 幾點實用提示

- **粵語咬字**：Suno 對粵語支援時好時壞，`natural Cantonese diction` 寫入 style 有幫助；出嚟如果變咗國語腔，試下將 style 改成 `Hong Kong Cantonese pop, 90s HK ballad style`，90 年代港式抒情歌喺訓練資料入面比例較高。
- **一次出兩首**：生成兩個 take，揀咬字較準嗰個，再用 Extend / Cover 補救個別段落。
- **升 key 副歌**：Suno 唔一定跟到「升全音」，可以生成完整首之後，將最後一次副歌單獨用 `key change` 提示再生成，或者後期用 DAW 移調。
- **長度**：呢個結構大約 3:40–4:20。如果出嚟太短，用 Extend 由 Bridge 接落去。

## 呢個 repo 嘅合成版本

`assets/audio/hand-in-smoke-vocal.wav` 係用自建 pipeline（TTS + 歌聲合成）出嘅 demo，用嚟試旋律、試速度、試 key。要真·唱歌質感，用上面嘅提示去 Suno 生成，再將成品放 `assets/audio/` 同更新 `songs.js` 嘅 `vocalAudio`。
