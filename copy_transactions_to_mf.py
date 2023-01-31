import datetime
import os
import platform

import dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
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

            # 「支出元」セレクトボックスの選択肢をすべて取得
            account_select = driver.find_element(By.ID, "user_asset_act_sub_account_id_hash")
            account_options = account_select.find_elements(By.TAG_NAME, "option")
            # account_text: セレクトボックスの選択肢。「ｘｘペイ」ではなく「ｘｘペイ(10,000円)」と残高が書かれているので、該当する選択肢を探す
            account_text = ""
            for option in account_options:
                # 選択肢(e.g. "ｘｘペイ(10,000円)")が、引数の支出元(e.g. "ｘｘペイ")と前方一致
                if option.text.startswith(account):
                    account_text = option.text
            if account_text == "":
                # 一致する選択肢がない場合: エラーを吐いて終了
                raise ValueError(f"Account '{account}' is not found!")
            Select(account_select).select_by_visible_text(account_text)  # 「支出元」を選択

            driver.find_element(By.ID, "js-content-field").send_keys(transaction["content"])  # 「内容」を入力
            driver.find_element(By.ID, "submit-button").click()  # 「保存する」をクリック
            driver.find_element(By.ID, "cancel-button").click()  # 保存が終了したら「閉じる」をクリック

        # ログアウト
        driver.get(MoneyForwardURL.SIGN_OUT)


def get_rakuten_cash_transactions(driver: webdriver.Chrome, target_date: datetime.date) -> list[dict]:
    """
    楽天ポイントクラブウェブサイトにログインし、楽天キャッシュの利用履歴を取得する

    Parameters
    ----------
    target_date: datetime.date
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

    # transactions: 楽天キャッシュの入出金履歴をappendしていく
    transactions: list[dict] = []
    for tr in trs:  # 各行について繰り返す
        if tr.get_attribute("class") not in ("get", "use"):
            continue  # 対象の行ではない

        tds = tr.find_elements(By.TAG_NAME, "td")
        # row_date: いま見ている行の日付
        row_date_str = "/".join(
            [
                tds[0].text[:4],  # year
                tds[0].text[5:7],  # month
                tds[0].text[8:10],  # day
            ]
        )
        row_date_dt = datetime.datetime.strptime(row_date_str, "%Y/%m/%d")
        row_date = datetime.date(row_date_dt.year, row_date_dt.month, row_date_dt.day)

        if row_date > target_date:
            # 対象日より新しいデータは無視する
            pass

        elif row_date == target_date:
            # 対象日のデータに対して処理を行う
            # 既定値
            # tr_is_income: Trueの場合は収入扱い
            tr_is_income = False
            # tr_content: 末尾についている"[2022/01/01]"という13文字を消す
            tr_content = tds[2].text[: len(tds[2].text) - 13]
            try:
                tr_amount = int(tds[4].text.replace(",", ""))  # 金額: 桁区切りコンマを削除する
            except Exception:
                tr_amount = 0  # データが含まれていない場合

            if tds[3].text == "チャージ\nキャッシュ":
                # 「チャージ（キャッシュ）」
                # tr_is_income = True
                # transactions.append(
                #     {
                #         "is_income": tr_is_income,
                #         "amount": tr_amount,
                #         "updated_at": row_date_str,
                #         "content": tr_content,
                #     }
                # )
                continue  # チャージはクレカの履歴から追えるので、ここでは取得しないこととした

            if tds[3].text == "利用":
                # 「利用」(街のお店でキャッシュを利用した場合)
                if len(tds[5].find_elements(By.CLASS_NAME, "note-icon")) > 0:
                    # "note-icon"クラスが存在する場合、「内訳（キャッシュ優先利用）」などで楽天キャッシュの利用額が書かれている
                    # 楽天キャッシュの支払額を取得
                    note_cash = tds[5].find_element(By.CLASS_NAME, "note-cash").text
                    tr_amount = int(note_cash.replace(",", "").replace("円", ""))  # 金額。桁区切りコンマと単位を削除する
                    # 明細の余分な文字列を除去
                    tr_content = tr_content.replace("楽天ペイでポイントを利用", "")
                    tr_content = tr_content.replace("で楽天ペイを利用しての購入によるポイント利用", "")
                    tr_content = tr_content.replace("でポイント利用", "")
                    transactions.append(
                        {
                            "is_income": tr_is_income,
                            "amount": tr_amount,
                            "updated_at": row_date_str,
                            "content": tr_content,
                        }
                    )
                elif tds[2].text[:13] == "投信積立（楽天キャッシュ）":
                    # "note-icon"クラスがなくても、投信積立（楽天キャッシュ）を利用している場合は取引がある
                    transactions.append(
                        {
                            "is_income": tr_is_income,
                            "amount": tr_amount,
                            "updated_at": row_date_str,
                            "content": tr_content,
                        }
                    )
                else:
                    # いずれも当てはまらない取引は追加しない
                    continue

        elif row_date < target_date:
            # 対象日以前のデータに達したら、収集を終了する
            break

    # ログアウト
    driver.get(RakutenCashURL.LOGOUT_PAGE)

    transactions.reverse()  # 新しい順に並んでいるので、古い順に並び替える
    return transactions


def main():
    # 実行対象は昨日
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    # envファイルの読み込み
    dotenv.load_dotenv()
    # ラズパイ(linux32)判定
    options = Options()
    if platform.system() == "Linux" and platform.machine() == "armv7l":  # if raspi
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.binary_location = "/usr/bin/chromium-browser"
        service = Service("/usr/bin/chromedriver")
    else:  # if not raspi and considering you're using Chrome
        service = Service(ChromeDriverManager().install())

    # 必ずプロセスを終了するようにしておく
    with webdriver.Chrome(service=service, options=options) as driver:
        # 昨日の楽天キャッシュ取引履歴を取得
        transactions = get_rakuten_cash_transactions(driver, yesterday)
        print(transactions)
        # マネーフォワードに反映
        post_money_forward_transactinos(driver, transactions, "楽天キャッシュ")


if __name__ == "__main__":
    # NOTE: 複数の金融機関に対応する場合は、ここで argparse を使って main に引数を渡すと良い
    main()
