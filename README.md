# theoretical-practical — 価格ウォッチ

Heritage Books の **Theoretical-Practical Theology, Volume 5（eBook 版）** の価格を
1日1回チェックし、**$28.00 を下回ったらメールで通知**します。

- 監視対象: https://heritagebooks.org/products/theoretical-practical-theology-volume-5
- しきい値: **$28.00 未満**（＝ $27.99 以下で通知）
- 実行時刻: 毎日 **08:07 JST**（GitHub Actions の schedule。数分〜十数分ずれることがあります）

## セットアップ（初回のみ・手作業が必要）

メールの認証情報は、リポジトリの Secrets に**ご本人が**登録してください。

1. Google アカウントで **2段階認証を有効化** →
   https://myaccount.google.com/apppasswords で「アプリ パスワード」を発行（16桁）
2. このリポジトリの
   **Settings → Secrets and variables → Actions → New repository secret**
   から、以下の3つを登録

   | Secret 名 | 中身 |
   |---|---|
   | `MAIL_USERNAME` | 送信元の Gmail アドレス |
   | `MAIL_PASSWORD` | 上で発行した**アプリ パスワード**（通常のログインパスワードではない） |
   | `MAIL_TO` | 通知の宛先アドレス（`MAIL_USERNAME` と同じでも可） |

3. **Actions** タブ → `price-watch` → **Run workflow** →
   `テスト用: 価格に関係なくメールを送る` に **チェックを入れて**実行し、
   メールが届くことを確認する

> Secrets は暗号化されて保存され、リポジトリが公開でも他人からは読めません。
> ログにも自動的にマスクされます。

## しきい値を変えたいとき

[.github/workflows/price-watch.yml](.github/workflows/price-watch.yml) の
`THRESHOLD_CENTS` を編集します（**セント単位**）。

```yaml
THRESHOLD_CENTS: "2800"   # $28.00。例: $25 にするなら "2500"
```

## 別の本も監視したいとき

同じワークフローの `PRODUCT_URL` を書き換えるか、`check` ジョブを複製します。
Heritage Books は Shopify なので、商品ページ URL がそのまま使えます。

## 仕組み

- [scripts/check_price.py](scripts/check_price.py) が
  Shopify の `/products/<handle>.js` から価格を取得します。
  HTML を解析しないので、サイトの見た目が変わっても壊れにくい作りです。
- 通知済みの価格は [data/state.json](data/state.json) に記録され、
  **同じ価格で毎日メールが飛ぶことはありません**。
  さらに値下がりした場合は改めて通知します。値段が $28 以上に戻ると、
  フラグが解除され、次に下がったときにまた通知されます。
- 毎回の価格は [data/price-log.csv](data/price-log.csv) に追記されます。

## 注意点

- **公開リポジトリの schedule ワークフローは、60日間リポジトリに活動がないと
  GitHub に自動で停止されます。** この構成では毎回 `data/price-log.csv` を
  commit するため活動が途切れませんが、停止された場合は GitHub からメールが届くので、
  Actions タブの「Enable workflow」ボタンで再開できます。
- 価格取得に失敗するとジョブが**失敗**します。GitHub から失敗通知が届くので、
  監視が黙って止まったままになることを避けられます。
- 監視しているのは **eBook 版**です。同じ巻のハードカバー版（$39.50）や
  5巻セット（$195.00）は別商品なので、監視対象には含まれていません。
