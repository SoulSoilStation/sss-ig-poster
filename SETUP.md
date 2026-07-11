# Instagram自動投稿 セットアップ手順（詳細版）

このリポジトリは **Instagram API with Instagram Login**（2024年以降のInstagram直接ログイン方式）を使います。
古い「Facebookログイン経由でPage Access Tokenを取得する」方式とは別物で、Facebookページの連携やGraph API Explorerでのトークン取得は不要です。
以下はすべて **ご自身のブラウザ・Instagram/Facebookアカウントで行う操作**です。所要時間の目安は15〜20分です。

---

## 1. Instagramをプロアカウント化する

1. スマホのInstagramアプリ →「設定とプライバシー」→「アカウントの種類とツール」→「プロアカウントに切り替える」
2. カテゴリを選び、アカウントタイプは「**ビジネス**」を選択

Facebookページとの連携は不要です（新方式ではInstagramアカウント単体で認証します）。

---

## 2. Meta for Developersでアプリを作成する（すでに完了済み）

`SoulSoilStation Poster` というアプリを作成済みで、ユースケースは「Instagramでメッセージとコンテンツを管理」を選択済みです。これでOKです。

---

## 3. Instagramアカウントを連携し、アクセストークンを発行する

1. https://developers.facebook.com/apps/ からアプリのダッシュボードを開く
2. 左メニューの「**Instagram**」をクリックして展開
3. 「**APIセットアップ（Instagramログイン）**」（英語表記: *API setup with Instagram Login*）を選択
   - 「**Facebookログインを使用したAPI設定**」の方は選ばないでください（別物の旧方式です）
4. ページ内の「アクセストークンを生成」的なセクションで「**Instagramアカウントを追加**」ボタンをクリック
5. ログインポップアップが表示されるので、**Instagramのビジネスアカウントのユーザー名・パスワードでログイン**（Facebookアカウントではありません）
6. 権限の許可画面が出たら内容を確認して「許可」
7. ダッシュボードに戻ると、連携されたInstagramアカウントの横に**アクセストークン**が表示されます
   - この画面から発行されるトークンは最初から**60日間有効な長期トークン**です（短期→長期への交換作業は不要）
8. 同じ画面に表示されている**ユーザーID**（数字の羅列）も控えてください

## 4. 必要な値の一覧

| 変数名 | 値の取得元 |
|---|---|
| `IG_ACCESS_TOKEN` | 手順3の7: 表示されたアクセストークン |
| `IG_USER_ID` | 手順3の8: 表示されたユーザーID |

---

## 5. GitHubリポジトリにSecretsとして登録する

1. https://github.com/SoulSoilStation/sss-ig-poster/settings/secrets/actions を開く
2. 「**New repository secret**」をクリック
3. Name欄に `IG_ACCESS_TOKEN`、Secret欄に手順3の値を入力して「Add secret」
4. 同様に `IG_USER_ID` も登録

---

## 6.（推奨）トークン自動延長のための GH_PAT を登録する

長期アクセストークンも60日で失効します。運用を止めないために、このリポジトリは**毎回の実行時にトークンを延長し、GitHub Secretsへ書き戻す**仕組みを持っています（`ig_refresh_token` という仕組みで、発行/前回延長から24時間以上経っていれば延長できます。毎日実行するので問題なく延長され続けます）。

1. https://github.com/settings/tokens を開く
2. 「**Generate new token**」→「**Generate new token (classic)**」を選択
3. Note（メモ）に `sss-ig-poster secret refresh` などと入力
4. Expiration（有効期限）は「No expiration」または長め（1年など）を選択
5. スコープ一覧から「**repo**」にチェック
6. 「**Generate token**」をクリックし、表示されたトークン文字列をコピー
7. 手順5と同じ画面で、Name `GH_PAT`、Secretに今コピーした値を入力して登録

**この手順を省略した場合**：自動延長は動作しません。60日ごとを目安に手順3を再実施して `IG_ACCESS_TOKEN` を手動更新してください。

---

## 7. 動作確認

1. https://github.com/SoulSoilStation/sss-ig-poster/actions を開く
2. 左側の「**Instagram自動投稿**」ワークフローをクリック
3. 「**Run workflow**」ボタン → ブランチ `main` のまま実行
4. 実行ログを確認し、エラーが出ていなければ実際にInstagramのフィードに投稿されているか確認する

うまくいかない場合は、実行ログに出るエラーメッセージを教えてください。

以降は毎日08:00 JSTに自動実行されます。
