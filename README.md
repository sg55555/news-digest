# Morning Brief — 毎朝ニュースダイジェスト

GitHub Actionsで毎朝7時に自動実行し、約137記事を収集してClaude APIで要約。上位10件を厳選してPWA対応のWebアプリで配信する個人向けニュースダイジェスト。

## 機能

- **自動収集・要約** — 毎朝7:00 JST（GitHub Actions）にRSSから137記事を取得し、Claude APIで要約
- **ソース** — NHK / Yahoo!ニュース / 東洋経済 / ITmedia / BBC / HackerNews / Google News（経済・技術）
- **深掘り** — 気になった記事をワンタップでClaude APIが追加分析
- **既読同期** — Supabaseで複数デバイス間の既読状態を同期
- **PWA対応** — ホーム画面に追加してアプリとして使用可能
- **週次ビュー** — 1週間分のアーカイブを閲覧

## 技術スタック

| カテゴリ | 技術 |
|---|---|
| フロントエンド | Vanilla HTML/CSS/JavaScript（PWA） |
| AI要約 | [Claude API](https://www.anthropic.com/) (claude-sonnet-4-6) |
| 自動実行 | [GitHub Actions](https://github.com/features/actions)（毎朝22:00 UTC） |
| 既読DB | [Supabase](https://supabase.com/) |
| ホスティング | [Vercel](https://vercel.com/)（`public/` を静的配信） |

## ファイル構成

```
news-digest/
├── .github/workflows/fetch-news.yml   # 毎朝22:00 UTC 自動実行
├── scripts/
│   ├── fetch_and_summarize.py         # RSS取得 → Claude要約 → news.json出力
│   └── inject-env.js                  # Vercelビルド時にSupabase環境変数を注入
├── public/
│   ├── index.html                     # メインUI
│   ├── news.json                      # 毎日上書き（GitHub Actionsが更新）
│   ├── manifest.json / sw.js          # PWA
│   └── icon-192.png / icon-512.png
├── package.json                       # Vercelのビルドコマンド定義（必須）
├── requirements.txt
└── vercel.json
```

## セットアップ

### GitHub Secrets（必須）

| シークレット名 | 説明 |
|---|---|
| `ANTHROPIC_API_KEY` | Claude APIキー |

### Vercel 環境変数（必須）

| 変数名 | 説明 |
|---|---|
| `SUPABASE_URL` | SupabaseプロジェクトURL |
| `SUPABASE_ANON_KEY` | Supabase匿名キー |

### Supabase テーブル

```sql
create table read_states (
  user_id text not null,
  article_id text not null,
  read_at timestamptz default now(),
  primary key (user_id, article_id)
);
```

## 仕組み

```
GitHub Actions（毎朝7:00 JST）
  └─ fetch_and_summarize.py
       ├─ RSSフィード137件を取得
       ├─ Claude APIでスコアリング・要約
       ├─ 上位10件を news.json に書き出し
       └─ news.json をコミット → Vercelが自動デプロイ
```

## 免責事項

個人利用を目的としたプロジェクトです。各ニュースソースの著作権は各メディアに帰属します。
