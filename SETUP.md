# Instagram自動投稿 セットアップ手順

Instagramへの投稿には Instagram Graph API（Meta for Developers）の認証情報が必要です。
以下はすべて **ご自身のブラウザ・Instagram/Facebookアカウントで行う操作**です（第三者が代行できません）。

## 1. Instagramをプロアカウント化してFacebookページと連携する

1. Instagramアプリ →「設定とプライバシー」→「アカウントの種類とツール」→「プロアカウントに切り替える」→ カテゴリは「ビジネス」を選択
2. 「アカウントセンター」→「連携済みのアカウント」からFacebookページと連携する
   - Facebookページを持っていない場合は先に作成してください（個人のFacebookアカウントとは別物です）

## 2. Meta for Developersでアプリを作成する

1. https://developers.facebook.com/apps/ にアクセス →「アプリを作成」
2. アプリタイプは「ビジネス」を選択して作成
3. ダッシュボードの「製品を追加」から **Instagram**（Instagram Graph API）を追加

※ アプリは「開発モード」のままで構いません。ご自身のアカウント（アプリのAdmin/Tester）に対しては、審査（App Review）なしでそのまま投稿できます。

## 3. アクセストークンを取得する

1. https://developers.facebook.com/tools/explorer/ を開く
2. 右上でご自身が作成したアプリを選択
3. 「User or Page」で自分を選択し、以下の権限を追加してトークンを生成
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_show_list`
   - `pages_read_engagement`
4. 「Generate Access Token」をクリックし、権限を許可 → 短期の**ユーザー**アクセストークンが発行される

## 4. 短期トークン → 長期トークンへ交換する

ブラウザで以下のURLにアクセス（`{}`部分をご自身の値に置き換え）:

```
https://graph.facebook.com/v23.0/oauth/access_token?grant_type=fb_exchange_token&client_id={アプリID}&client_secret={アプリシークレット}&fb_exchange_token={手順3の短期トークン}
```

- アプリID / アプリシークレットは、アプリのダッシュボード「設定」→「ベーシック」で確認できます
- レスポンスの `access_token` が60日間有効な**長期ユーザートークン**です

## 5. Facebookページ・Instagramビジネスアカウント情報を取得する

Graph API Explorer（手順3の画面）で、アクセストークンを手順4の長期トークンに差し替えたうえで以下を実行:

1. `GET /me/accounts`
   → 対象のFacebookページの `id`（Page ID）と `access_token`（**これが長期のPageアクセストークン = `IG_ACCESS_TOKEN`**）を控える
2. `GET /{Page ID}?fields=instagram_business_account`
   → `instagram_business_account.id` が `IG_BUSINESS_ACCOUNT_ID`

## 6. 必要な値の一覧

| 変数名 | 取得元 |
|---|---|
| `IG_APP_ID` | アプリの設定 → ベーシック |
| `IG_APP_SECRET` | アプリの設定 → ベーシック |
| `IG_ACCESS_TOKEN` | 手順5の `/me/accounts` レスポンスの `access_token` |
| `IG_BUSINESS_ACCOUNT_ID` | 手順5の `instagram_business_account.id` |

## 7. GitHubリポジトリにSecretsとして登録する

リポジトリの `Settings` → `Secrets and variables` → `Actions` → `New repository secret` から、上記4つをそれぞれ登録してください。

## 8.（推奨）トークン自動延長のためのGH_PATを登録する

長期トークンも60日で失効します。運用を止めないために、毎回の実行時に自動延長してSecretsへ書き戻す仕組みを組み込んでいます。これを有効にするには:

1. https://github.com/settings/tokens →「Generate new token (classic)」
2. スコープは `repo` を選択（Secretsの更新に必要）
3. 生成したトークンをリポジトリSecretsに `GH_PAT` という名前で登録

**設定しない場合**は自動延長機能は動作せず、60日以内を目安に手順3〜5を再実施して `IG_ACCESS_TOKEN` を手動更新してください（放置すると60日後に投稿が失敗し始めます）。

## 9. 動作確認

1. GitHubリポジトリの `Actions` タブ →「Instagram自動投稿」ワークフローを選択
2. 「Run workflow」ボタンで手動実行
3. 実行ログを確認し、実際にInstagramへ投稿されるか確認する

以降は毎日08:00 JSTに自動実行されます。
