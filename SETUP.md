# Instagram自動投稿 セットアップ手順（詳細版）

Instagramへの投稿には Instagram Graph API（Meta for Developers）の認証情報が必要です。
以下はすべて **ご自身のブラウザ・Instagram/Facebookアカウントで行う操作**です（第三者が代行できません）。
所要時間の目安は20〜30分です。

---

## 1. Instagramをプロアカウント化してFacebookページと連携する

1. スマホのInstagramアプリを開き、自分のプロフィール画面右上の **☰（三本線メニュー）** をタップ
2. 「**設定とプライバシー**」→「**アカウントの種類とツール**」をタップ
3. 「**プロアカウントに切り替える**」をタップし、案内に従って進む
   - カテゴリ選択画面が出たら、任意のカテゴリ（例: 「園芸用品店」「ブログ」など）を選び、
     アカウントタイプは **「ビジネス」** を選択（「クリエイター」ではなくビジネス推奨）
4. 途中で「Facebookページと接続しますか？」と聞かれるので、
   - すでにSoulSoilStation用のFacebookページを持っていればそれを選択
   - 持っていなければ「新しいFacebookページを作成」を選んでその場で作成（ページ名は何でもOK、例: SoulSoilStation）
5. 完了後、Instagramの「設定とプライバシー」→「アカウントセンター」→「連携済みのアカウント」を開き、
   Facebookページがリンクされていることを確認する

> すでにプロアカウント化・ページ連携済みの場合はこの手順は不要です。

---

## 2. Meta for Developersでアプリを作成する

1. PCのブラウザで https://developers.facebook.com/apps/ を開く
   - 手順1で使ったFacebookアカウント（ページの管理者アカウント）でログインしていることを確認
2. 右上（または中央）の「**アプリを作成**」ボタンをクリック
3. 「アプリの用途は？」と聞かれたら「**他のユーザーに代わってアプリを管理する**」または「**ビジネス**」を選択
   - 画面文言はMetaのアップデートで変わることがありますが、要は「ビジネス用アプリ」を選べばOK
4. アプリ名を入力（例: `SoulSoilStation IG Poster`）、連絡先メールアドレスを入力
5. 「ビジネスポートフォリオに接続」は、既存のものがあれば選択、なければ「後で接続」でスキップ可
6. 「アプリを作成」をクリック（パスワード再入力を求められることがあります）

作成後、アプリのダッシュボード画面に遷移します。

---

## 3. Instagram製品をアプリに追加する

1. アプリのダッシュボード左メニューの「**製品を追加**」（Add Product）をクリック
2. 一覧から「**Instagram**」のカードを探し、「**設定**」（Set up）をクリックして追加
   - これで `instagram_basic` や `instagram_content_publish` の権限がこのアプリで使えるようになります

> ※ アプリは「開発モード」のままで問題ありません。ご自身のアカウント（アプリの管理者）に対する投稿であれば、
> Metaの審査（App Review）は不要でそのまま使えます。第三者アカウントへの投稿を始めるときだけ審査が必要になります。

---

## 4. アプリID・アプリシークレットを控える

1. 左メニュー「**設定**」→「**ベーシック**」を開く
2. 画面上部に「**アプリID**」が表示されている → これが `IG_APP_ID`
3. 「**app secret**（アプリシークレット）」の横の「**表示**」をクリック（Facebookパスワードの再入力を求められます）
4. 表示された文字列が `IG_APP_SECRET`

この2つはこの後すぐ使うので、一時的にメモ帳などに控えておいてください（最終的にはGitHub Secretsに保存し、平文では残さないようにします）。

---

## 5. Graph API Explorerでアクセストークンを取得する

1. https://developers.facebook.com/tools/explorer/ を開く
2. 画面右上（または上部）の「**Meta App**」ドロップダウンで、手順2で作ったアプリを選択
3. 「**User or Page**」ドロップダウンで「**User Token**」（自分のユーザートークン）を選択
4. 「**Permissions（権限）**」の入力欄・チェックリストから、以下を検索して追加（チェックを付ける）:
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_show_list`
   - `pages_read_engagement`
5. 「**Generate Access Token**」ボタンをクリック
6. Facebookのログイン確認・権限許可のポップアップが出るので、内容を確認して「**続行**」「**許可**」を選択
   - 対象のFacebookページを選ぶ画面が出たら、手順1で連携したページを選択
7. Explorer画面の「Access Token」欄に文字列が入る → これが**短期（約1時間有効）のユーザートークン**

> このトークンはこの後の手順6ですぐ使い切るので、コピーしておいてください。

---

## 6. 短期トークンを長期トークンに交換する

Graph API Explorerの中央の入力欄（パス欄）に、以下を **`{}`部分を実際の値に置き換えて** 入力し、GETで実行します。

```
oauth/access_token?grant_type=fb_exchange_token&client_id={手順4のIG_APP_ID}&client_secret={手順4のIG_APP_SECRET}&fb_exchange_token={手順5の短期トークン}
```

- 入力後、Explorerの「Submit」ボタン（青い送信ボタン）をクリック
- 右側にJSONが返り、`"access_token": "..."` という値が表示される
- これが **60日間有効な長期ユーザートークン** です。コピーしてください。

（Explorerでうまく動かない場合は、上記URLの先頭に `https://graph.facebook.com/v23.0/` を付けてブラウザのアドレスバーに直接貼り付けてアクセスしても同じ結果が得られます）

---

## 7. FacebookページIDと長期Pageアクセストークンを取得する

1. Explorerの「Access Token」欄を、手順6で取得した**長期ユーザートークン**に手動で貼り替える
   （Explorer右上の鉛筆アイコンやトークン欄を編集して上書きできます）
2. パス欄に `me/accounts` と入力してSubmit
3. JSONレスポンスの `data` 配列の中に、手順1で連携したページの情報が入っている:
   ```json
   {
     "data": [
       {
         "access_token": "EAAxxxxxxxx...",
         "id": "123456789012345",
         "name": "SoulSoilStation"
       }
     ]
   }
   ```
   - `access_token` → これが **`IG_ACCESS_TOKEN`**（長期のPageアクセストークン）
   - `id` → Facebookページ ID（次の手順で使う）

---

## 8. Instagramビジネスアカウント ID を取得する

1. パス欄に `{手順7のページID}?fields=instagram_business_account` と入力してSubmit
   （例: `123456789012345?fields=instagram_business_account`）
2. レスポンス例:
   ```json
   {
     "instagram_business_account": { "id": "17841400000000000" },
     "id": "123456789012345"
   }
   ```
   - `instagram_business_account.id` → これが **`IG_BUSINESS_ACCOUNT_ID`**

もしこのフィールドが空・エラーになる場合は、手順1のFacebookページ⇔Instagramプロアカウントの連携ができていない可能性があります。手順1に戻って確認してください。

---

## 9. 取得した値の一覧

ここまでで以下の4つが揃っているはずです。

| 変数名 | 値の取得元 |
|---|---|
| `IG_APP_ID` | 手順4：アプリ設定 → ベーシック |
| `IG_APP_SECRET` | 手順4：アプリ設定 → ベーシック（表示ボタン） |
| `IG_ACCESS_TOKEN` | 手順7：`/me/accounts` レスポンスの `access_token` |
| `IG_BUSINESS_ACCOUNT_ID` | 手順8：`instagram_business_account.id` |

---

## 10. GitHubリポジトリにSecretsとして登録する

1. https://github.com/SoulSoilStation/sss-ig-poster/settings/secrets/actions を開く
2. 「**New repository secret**」をクリック
3. Name欄に `IG_APP_ID`、Secret欄に手順4の値を入力して「Add secret」
4. 同様に `IG_APP_SECRET` / `IG_ACCESS_TOKEN` / `IG_BUSINESS_ACCOUNT_ID` をそれぞれ登録（計4つ）

---

## 11.（推奨）トークン自動延長のための GH_PAT を登録する

長期Pageアクセストークンも理論上60日で失効する可能性があります。運用を止めないために、
このリポジトリは**毎回の実行時にトークンを自動延長し、GitHub Secretsへ書き戻す**仕組みを持っています。
これを有効にするには、Secretsを書き換える権限を持つ個人アクセストークン（PAT）が必要です。

1. https://github.com/settings/tokens を開く（自分のGitHubアカウントの設定）
2. 「**Generate new token**」→「**Generate new token (classic)**」を選択
3. Note（メモ）に `sss-ig-poster secret refresh` などと入力
4. Expiration（有効期限）は「No expiration」または長め（1年など）を選択
5. スコープ一覧から「**repo**」にチェック（Secretsの更新に必要な権限一式が含まれます）
6. 「**Generate token**」をクリックし、表示されたトークン文字列をコピー（**この画面を閉じると二度と表示されないので注意**）
7. 手順10と同じ画面で、Name `GH_PAT`、Secretに今コピーした値を入力して登録

**この手順を省略した場合**：自動延長は動作しません。60日ごとを目安に手順5〜9を再実施して
`IG_ACCESS_TOKEN` を手動で更新してください（放置すると60日後から投稿が失敗するようになります）。

---

## 12. 動作確認

1. https://github.com/SoulSoilStation/sss-ig-poster/actions を開く
2. 左側の「**Instagram自動投稿**」ワークフローをクリック
3. 右側の「**Run workflow**」ボタン → ブランチ `main` のまま「Run workflow」を実行
4. 数十秒後に一覧に実行結果が表示されるのでクリックし、ログを確認
5. エラーが出ていなければ、実際にInstagramのフィードに投稿されているか確認する

うまくいかない場合は、実行ログに出るエラーメッセージ（特にGraph APIからのエラー文言）を教えてください。原因を切り分けます。

以降は毎日08:00 JSTに自動実行されます。
