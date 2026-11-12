# お昼のひとこと法話集

短い法話を毎日ひとつ残し、読み返したり、人に渡したりするための静的サイトです。GitHub Pages が `main` ブランチのルートを、そのまま配信します。公開のときにビルドは走りません。

法話の文章・出典・挿絵の説明は、すべて `data/episodes.json` に書いたものがページにそのまま出ます。スクリプトが文を足したり、引用を作ったりすることはありません。

## ローカルで見る

初回だけ、サムネイル作成に使う Pillow を入れます。

```bash
pip install -r requirements.txt
python3 scripts/build.py
python3 -m http.server 8000
```

ブラウザで <http://localhost:8000/> を開きます。ファイルをダブルクリックして開くのではなく、このサーバー経由で見てください。

## 新しい法話を追加する

毎日、次の順で 1 回分を足します。

### 1. 挿絵を `images/` に置く

ファイル名は半角の英数字とハイフンだけにし、拡張子は `.jpg` にします。例: `images/05-example.jpg`

幅はおよそ 1200px にしてください。それより大きい写真は、次で縮小・圧縮します。

```bash
python3 scripts/optimize_image.py 元の画像.jpg images/05-example.jpg
```

幅がすでに 1200px 前後なら、その JPEG を `images/` に置くだけで構いません。1300px を超えていると、次の生成でエラーになります。

### 2. `data/episodes.json` の末尾に 1 件足す

`episodes` 配列の**最後**に、次の形のオブジェクトを追加します。配列の順番は表示に使いません。`number` が大きい回が新しい回で、一覧の先頭に出ます。

```json
{
  "number": 5,
  "title": "題名",
  "date": "2026年11月13日",
  "image": "05-example.jpg",
  "imageAlt": "挿絵が何を描いているかの説明",
  "source": "その回全体の出典",
  "blocks": [
    {
      "type": "paragraph",
      "text": "本文の段落です。段落が続くときは、この形を必要な数だけ並べます。"
    },
    {
      "type": "quote",
      "text": "「引用文」",
      "source": "その引用の出典"
    }
  ],
  "daily": "暮らしのひとことの文章です。"
}
```

上の文面は見本です。この README に書いてあるだけではページには出ません。`episodes.json` に書いたものだけが掲載されます。

項目の意味:

| 項目 | 書き方 |
| --- | --- |
| `number` | 回番号。既存の最大値に 1 を足す。ページは `episodes/005.html` のように 3 桁になる。 |
| `title` | 題名。「第5回」は書かない。ページ側で番号を付ける。 |
| `date` | `2026年11月13日` の形。見出しの「配信日」にそのまま出る。 |
| `image` | `images/` に置いたファイル名だけ。フォルダ名は書かない。 |
| `imageAlt` | 挿絵の説明。画像の代替テキストになる。 |
| `source` | その回の出典。題名の下の「出典」欄に、全文がそのまま出る。 |
| `blocks` | 本文。上からこの順に表示する。 |
| `blocks[].type` | 地の文は `paragraph`、引用は `quote`。 |
| `blocks[].text` | 段落、または引用文。引用符「」も、出したい場合はここに含める。スクリプトは引用符を足さない。 |
| `blocks[].source` | 引用のとき必須。引用のすぐ横に「出典」として出る。空だと生成が止まる。 |
| `daily` | 「暮らしのひとこと」の本文。 |

引用がない回は、`paragraph` だけを並べます。引用がある回は、読ませたい位置に `quote` を挟みます。

### 3. ページを生成する

```bash
python3 scripts/build.py
```

これで次がまとめて更新されます。

- `index.html`（新しい回が先頭。いちばん新しい回だけ挿絵を大きくし、暮らしのひとことも載せる。それ以外はサムネイルと題名）
- `episodes/005.html`（その回のページ。前後の回へのリンク付き）
- 前後の回のページのリンク
- `images/thumbs/`（一覧用の縮小画像）

`index.html` と `episodes/*.html` は手で編集しないでください。直したい文章は `data/episodes.json` を編集して、もう一度 `python3 scripts/build.py` を実行します。

### 4. ブラウザで確認する

`python3 -m http.server 8000` で開き、少なくとも次を見ます。

- 一覧の先頭が、いま足した回である
- その回のページに、挿絵・題名・配信日・「出典」・本文・暮らしのひとことがある
- 引用を書いた場合、引用のすぐ横に、その `source` が「出典」として出ている
- フッターの注記が 4 つ残っている
- 一つ前の回・一つ後の回へのリンクが、あるべき側だけにある
- 携帯電話の幅でも、横にスクロールしない

### 5. `main` に載せる

生成したファイルも一緒にコミットします。Pages はリポジトリに入っている HTML をそのまま出します。

```bash
git add data/episodes.json images/05-example.jpg images/thumbs/05-example.jpg index.html episodes
git commit -m "第5回を追加"
git push origin main
```

`git diff` に `404.html` や前後の回の HTML も出ていれば、それも加えてください。force push は不要です。

push すると GitHub Actions が、HTML が `data/episodes.json` から作り直したものと一致するかを確認します。JSON だけ直して生成を忘れると、そこで失敗します。

## フッターの注記

全ページの末尾に出る 4 項目は、`site.notes` です。法華経の訳、日蓮聖人の御文の出典の扱い、個人の学びであることの断り、挿絵が画像生成であることの断りが書いてあります。文言を変えるときも、ここを編集してから `python3 scripts/build.py` を実行します。

## ファイル

| ファイル | 役割 |
| --- | --- |
| `data/episodes.json` | 法話の原本。普段編集するのはここだけ。 |
| `scripts/build.py` | JSON から HTML とサムネイルを作る。 |
| `scripts/optimize_image.py` | 大きい挿絵を幅およそ 1200px の JPEG にする。 |
| `index.html` | 一覧。生成物。 |
| `episodes/001.html` など | 各回のページ。生成物。 |
| `images/` | 各回の挿絵（およそ 1200px）。 |
| `images/thumbs/` | 一覧用の縮小画像。生成物。 |
| `css/style.css` | 見た目。 |
| `404.html` | 見つからないページ。生成物。 |
| `.nojekyll` | GitHub Pages に Jekyll を通させないための空ファイル。 |

## GitHub Pages

リポジトリの Settings → Pages → Build and deployment で、Source を **Deploy from a branch**、Branch を **`main`**、Folder を **`/ (root)`** にします。

公開先は <https://mlabpages.github.io/ohiru-howa/> です。別の URL にするときは、`data/episodes.json` の `site.url` も同じアドレスに直し、`python3 scripts/build.py` を実行してから push します。`site.url` は共有したときの URL と、各ページの canonical に使います。
