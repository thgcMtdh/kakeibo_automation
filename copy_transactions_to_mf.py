import datetime
import os

import dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from webdriver_manager.chrome import ChromeDriverManager


class MoneyForwardURL:
    """MoneyForward のURL"""

    TOP_PAGE = "https://moneyforward.com/"
    SIGN_IN = TOP_PAGE + "sign_in"
    SIGN_OUT = TOP_PAGE + "sign_out"
    CF_PAGE = TOP_PAGE + "cf"


class RakutenCashURL:
    TOP_PAGE = "https://point.rakuten.co.jp/"
    HISTORY = TOP_PAGE + "history/"
    LOGOUT_PAGE = "https://member.id.rakuten.co.jp/r/logout.html"


def post_money_forward_transactinos(driver: webdriver.Chrome, transactions: list[dict], account: str) -> None:
    """
    マネーフォワード家計簿にログインし、入出金履歴を登録する

    Parameters
    ----------
    transactions: list[dict]
        取引履歴を表す key-value object を0個以上含んだリスト。履歴がない場合は `[]` を返す。
        object は [マネーフォワードAPI](https://github.com/moneyforward/api-doc/blob/master/transactions_create.md)
        を参考にした書式で、以下のパラメータを必須キーとして含む

        {
            "is_income": True,                # 入金の場合; `True`, 出金の場合; `False`
            "amount": 1000,                   # 金額; 0または正の整数
            "updated_at": "2022/01/01",       # 入出金日; yyyy/mm/dd形式の文字列
            "content": "ドラッグストアｘｘ店",  # 入出金内容を表す文字列
        }
    """

    if transactions != []:
        driver.implicitly_wait(10)
        driver.set_page_load_timeout(10)

        # ログイン
        driver.get(MoneyForwardURL.SIGN_IN)
        ID = os.environ["MONEYFORWARD_ID"]
        PWD = os.environ["MONEYFORWARD_PASS"]
        driver.find_element(By.XPATH, "/html/body/main/div/div/div/div/div[1]/section/div/div/div[2]/div/a[1]").click()
        driver.find_element(By.NAME, "mfid_user[email]").send_keys(ID)
        driver.find_element(By.CLASS_NAME, "submitBtn").click()
        driver.find_element(By.NAME, "mfid_user[password]").send_keys(PWD)
        driver.find_element(By.CLASS_NAME, "submitBtn").click()

        # データ入力
        driver.get(MoneyForwardURL.CF_PAGE)
        for transaction in transactions:
            driver.find_element(
                By.XPATH, "/html/body/div[1]/div[2]/div/div/div/section/section/div[1]/div[1]/div/button"
            ).click()  # 「手入力」ボタンをクリック

            if transaction["is_income"]:
                driver.find_element(By.ID, "info").click()  # 収入タブに移動
            else:
                driver.find_element(By.ID, "important").click()  # 支出タブに移動

            driver.find_element(By.ID, "updated-at").clear()
            driver.find_element(By.ID, "updated-at").send_keys(transaction["updated_at"])
            driver.find_element(By.ID, "appendedPrependedInput").send_keys(transaction["amount"])

            accountSelect = driver.find_element(By.ID, "user_asset_act_sub_account_id_hash")  # 「支出元」セレクトボックス
            accountOptions = accountSelect.find_elements(By.TAG_NAME, "option")  # 「支出元」の選択肢をすべて取得
            accountText = ""  # セレクトボックスの選択肢。「ｘｘペイ」ではなく「ｘｘペイ(10,000円)」と残高が書かれているので、該当する選択肢を探す
            for option in accountOptions:
                if option.text.startswith(account):  # 選択肢(e.g. "ｘｘペイ(10,000円)")が、引数の支出元(e.g. "ｘｘペイ")と前方一致
                    accountText = option.text
            if accountText == "":  # 一致する選択肢がない場合はエラーを吐いて終了
                raise ValueError("Account '" + account + "' is not found!")
            Select(accountSelect).select_by_visible_text(accountText)  # 「支出元」を選択

            driver.find_element(By.ID, "js-content-field").send_keys(transaction["content"])  # 「内容」を入力
            driver.find_element(By.ID, "submit-button").click()  # 「保存する」をクリック
            driver.find_element(By.ID, "cancel-button").click()  # 保存が終了したら「閉じる」をクリック

        # ログアウト
        driver.get(MoneyForwardURL.SIGN_OUT)


def get_rakuten_cash_transactions(driver: webdriver.Chrome, targetDate: datetime.date) -> list[dict]:
    """
    楽天ポイントクラブウェブサイトにログインし、楽天キャッシュの利用履歴を取得する

    Parameters
    ----------
    targetDate: datetime.date
        データを取得する日付

    Returns
    -------
    transactions: list[object]
        取引履歴を表す key-value object を0個以上含んだリスト。
        詳細は post_money_forward_transaction 関数を参照
    """
    driver.implicitly_wait(10)
    driver.set_page_load_timeout(10)
    driver.get(RakutenCashURL.HISTORY)

    # ログイン
    ID = os.environ["RAKUTEN_ID"]
    PWD = os.environ["RAKUTEN_PASS"]
    driver.find_element(By.ID, "loginInner_u").send_keys(ID)
    driver.find_element(By.ID, "loginInner_p").send_keys(PWD)
    driver.find_element(By.NAME, "submit").click()

    # 入出金明細の取得
    table = driver.find_element(By.XPATH, "/html/body/div[2]/div/div[2]/div/div/div/table")
    trs = table.find_elements(By.TAG_NAME, "tr")  # ポイント履歴の表の各行を配列として取得

    transactions: list[dict] = []  # ここに楽天キャッシュの入出金履歴をappendしていく
    for tr in trs:  # 各行について繰り返す
        if tr.get_attribute("class") == "get" or tr.get_attribute("class") == "use":
            tds = tr.find_elements(By.TAG_NAME, "td")
            year = tds[0].text[:4]
            month = tds[0].text[5:7]
            day = tds[0].text[8:10]
            rowDate = datetime.date(int(year), int(month), int(day))  # いま見ている行の日付

            if rowDate > targetDate:  # 対象日より新しいデータは無視する
                pass

            elif rowDate == targetDate:  # 対象日のデータに対して処理を行う
                # 「チャージ（キャッシュ）」
                if tds[3].text == "チャージ\nキャッシュ":
                    transactions.append(
                        {
                            "is_income": True,
                            "amount": int(tds[4].text.replace(",", "")),  # 金額。桁区切りコンマを削除する
                            "updated_at": targetDate.strftime("%Y/%m/%d"),  # 日付。対象日をyyyy/mm/dd形式にする
                            "content": tds[2].text[: len(tds[2].text) - 13],  # 内容。末尾についている"[2022/01/01]"という13文字を消す
                        }
                    )

                # 「利用」(街のお店でキャッシュを利用した場合)
                elif tds[3].text == "利用":
                    # "note-icon"クラスが存在する場合、「内訳（キャッシュ優先利用）」などで楽天キャッシュの利用額が書かれている
                    if len(tds[5].find_elements(By.CLASS_NAME, "note-icon")) > 0:
                        noteCash = tds[5].find_element(By.CLASS_NAME, "note-cash").text  # 楽天キャッシュの支払額を取得
                        content = tds[2].text[: len(tds[2].text) - 13]  # 内容。末尾についている日付と注釈を消す
                        content = content.replace("楽天ペイでポイントを利用", "")
                        content = content.replace("で楽天ペイを利用しての購入によるポイント利用", "")
                        content = content.replace("でポイント利用", "")
                        transactions.append(
                            {
                                "is_income": False,
                                "amount": int(noteCash.replace(",", "").replace("円", "")),  # 金額。桁区切りコンマと円を削除する
                                "updated_at": targetDate.strftime("%Y/%m/%d"),  # 日付。対象日をyyyy/mm/dd形式にする
                                "content": content,
                            }
                        )

                    # "note-icon"クラスがなくても、投信積立（楽天キャッシュ）を利用している場合は取引がある
                    elif tds[2].text[:13] == "投信積立（楽天キャッシュ）":
                        transactions.append(
                            {
                                "is_income": False,
                                "amount": int(tds[4].text.replace(",", "")),  # 金額。桁区切りコンマを削除する
                                "updated_at": targetDate.strftime("%Y/%m/%d"),  # 日付。対象日をyyyy/mm/dd形式にする
                                "content": tds[2].text[: len(tds[2].text) - 13],  # 内容。末尾についている"[2022/01/01]"という13文字を消す
                            }
                        )

            else:  # 対象日以前のデータに達したら、収集を終了する
                break

    driver.get(RakutenCashURL.LOGOUT_PAGE)  # ログアウト

    transactions.reverse()  # 新しい順に並んでいるので、古い順に並び替える
    return transactions


def main():
    # 実行対象は昨日
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    # envファイルの読み込み
    dotenv.load_dotenv()
    # 必ずプロセスを終了するようにしておく
    with webdriver.Chrome(ChromeDriverManager().install()) as driver:
        # 昨日の楽天キャッシュ取引履歴を取得
        transactions = get_rakuten_cash_transactions(driver, yesterday)
        print(transactions)
        # マネーフォワードに反映
        post_money_forward_transactinos(driver, transactions, "楽天キャッシュ")


if __name__ == "__main__":
    # NOTE: 複数の金融機関に対応する場合は、ここで argparse を使って main に引数を渡すと良い
    main()
