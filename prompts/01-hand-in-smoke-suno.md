# 《濃煙裡的手》— Suno 複製貼上包

照住下面四格填，兩分鐘出成品。全部內容都可以直接複製。

---

## 1. Title（標題）

```
濃煙裡的手
```

## 2. Style of Music（風格）

**首選（完整版）**

```
Cantonese pop ballad, Hong Kong Cantonese diction, male lead vocal, 76 BPM, 4/4, C major, intimate grand piano intro, warm string pad, soft brush drums entering verse 2, restrained verses, wide emotional chorus, subtle electric guitar arpeggio, cinematic bridge build, key change up a whole step on final chorus, breathy sincere delivery, natural vibrato, analogue warmth, wide stereo mix, emotional, cinematic
```

**如果咬字變咗國語腔（備用版）**

```
90s Hong Kong Cantonese ballad, male vocal, 76 BPM, piano and strings, sentimental, retro HK pop production, Cantonese lyrics, natural Cantonese pronunciation, live drum kit, warm tape saturation, emotional climax
```

**太長貼唔落就用呢個短版**

```
Cantonese pop ballad, male vocal, 76 BPM, piano and strings, emotional build, cinematic chorus
```

## 3. Exclude Styles（排除）

```
EDM, trap, rap, autotune, heavy distortion, female vocal, Mandarin pronunciation, children choir
```

## 4. Lyrics（歌詞，連段落標籤）

```
[Intro]
(piano, 4 bars)

[Verse 1]
凌晨三點，鐘聲一響
鞋都未着好，就跳上車廂
街燈向後退，我望住窗外
唔係唔驚，只怕慢咗一秒

[Pre-Chorus]
手機入面，老婆留咗句
「記得食飯，記得返嚟」
我冇時間覆，只係望一望
然後戴上面罩，走入呢片灰

[Chorus]
濃煙裡面，我伸手搵你
睇唔到路，都要行前多一呎
如果呢個城市，仲有人等緊返屋企
就算熏到眼痛，都唔會放開你

你唔使驚，我跟住你背脊
一步一步，我哋行返出去
如果呢個城市，仲有人肯為人留低
我呢條命，就唔算白過一日

[Verse 2]
十八樓，走廊已經塌咗
條水喉扯到盡，手心都震
有個細路，攬實我隻腳
佢話：「叔叔，我媽媽仲喺裡面。」

[Pre-Chorus]
我冇講嘢，只係點一點頭
抱起佢，交俾下一個兄弟
轉身再入去，熱到面罩都溶
但我記得，佢媽媽對眼

[Chorus]
濃煙裡面，我伸手搵你
睇唔到路，都要行前多一呎
如果呢個城市，仲有人等緊返屋企
就算熏到眼痛，都唔會放開你

[Bridge]
唔係想做英雄
只係有人要救
每次行入去
都可能冇得行返出嚟
但有一句，我哋冇寫喺牆上
先救人，後講自己

[Chorus]
濃煙裡面，我伸手搵你
睇唔到路，都要行前多一呎
如果呢個城市，仲有人等緊返屋企
就算熏到眼痛，都唔會放開你

[Outro]
天光嘅時候，火已經熄
我坐喺路邊，除低頂帽
有人遞支水，講聲「多謝你」
我笑一笑，話：「呢啲係我哋嘅工作。」
然後望住個天，等下一次鐘聲
(piano out)
```

---

## 出嚟之後點做

1. **生成兩首**，揀咬字較清楚嗰首（粵語咬字係最大變數）
2. 太短就 **Extend**，由 `[Bridge]` 接落去
3. 最後一次副歌冇升 key 都收貨，唔需要為咗升 key 重生成
4. 下載 **MP3 或 M4A**（唔好下載影片）

## 拿到檔案之後

把 mp3 / m4a 放入對話（或放喺 workspace 任何位置），同我講一聲。我會：

- 放去 `assets/audio/hand-in-smoke-suno.m4a`（瀏覽器原生支援 mp3/m4a，唔需要轉檔）
- 改 `assets/songs.js` 嘅 `vocalAudio` 指去新檔
- 網站即刻變成「真·唱歌版」，原本嘅合成 demo 保留做備份
- 順手更新 README 同 Suno 提示包，記低用咗邊個 style 同 take

## 為咩歌詞要加逗號

Suno 會跟標點斷句。原本歌詞用全角空格（　）分隔詞組，模型有機會當成一個長句、或者斷錯位。改成逗號之後，每句嘅呼吸位同旋律落點會貼近我寫嘅拍子（76 BPM，四拍一句）。
