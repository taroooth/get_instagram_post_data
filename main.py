import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import math
from gspread_formatting import *
import pytz

import os
import shutil
import stat
from pathlib import Path
from selenium import webdriver
import re

import config

# 項目アルファベット
delete_post_column = 'A'
keyword_column = 'B'
elapsed_time_column = 'C'
created_time_column = 'D'
user_name_column = 'E'
follower_count_column = 'F'
like_count_column = 'G'
comment_count_column = 'H'
permalink_column = 'I'

global driver


def add_execute_permission(path: Path, target: str = "u"):
    """Add `x` (`execute`) permission to specified targets."""
    mode_map = {
        "u": stat.S_IXUSR,
        "g": stat.S_IXGRP,
        "o": stat.S_IXOTH,
        "a": stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
    }

    mode = path.stat().st_mode
    for t in target:
        mode |= mode_map[t]

    path.chmod(mode)


def settingDriver():
    print("driver setting")
    global driver

    driverPath = "/tmp" + "/chromedriver"
    headlessPath = "/tmp" + "/headless-chromium"

    print("copy headless-chromium")
    shutil.copyfile(os.getcwd() + "/headless-chromium", headlessPath)
    add_execute_permission(Path(headlessPath), "ug")

    print("copy chromedriver")
    shutil.copyfile(os.getcwd() + "/chromedriver", driverPath)
    add_execute_permission(Path(driverPath), "ug")

    chrome_options = webdriver.ChromeOptions()

    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1280x1696")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--hide-scrollbars")
    chrome_options.add_argument("--enable-logging")
    chrome_options.add_argument("--log-level=0")
    chrome_options.add_argument("--v=99")
    chrome_options.add_argument("--single-process")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--disable-dev-shm-usage")

    chrome_options.binary_location = headlessPath

    print("get driver")
    driver = webdriver.Chrome(driverPath, chrome_options=chrome_options)

# 文字列検索
def get_search_value(ptn, str):

    result = re.search(ptn, str)

    if result:
        return result.group(1)
    else:
        return None

# ユーザネーム取得
def get_user_name(url):
    global driver
    try:
        driver.get(url)

        driver.implicitly_wait(10)
        html = driver.page_source
        name = get_search_value(r'\(@(.+)\)のInstagramアカウント', html)
        print(type(name))
    finally:
        print("driver quit")
        driver.quit()

    print('ユーザー名: ' + name)
    return name

# フォロワー数取得

def get_follower_count(user_name):
    url = "https://www.instagram.com/" + user_name + "/"
    global driver
    try:
        driver.get(url)

        driver.implicitly_wait(10)

        html = driver.page_source
        count = get_search_value(r'"フォロワー(.+)人、フォロー中', html)
    finally:
        print("driver quit")
        driver.quit()
    return count

# 新規シート作成
def create_worksheet(data):
    today = datetime.today()
    old_day = today - timedelta(days=30)
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    jsonf = "instagram-for-influencer-d2613e5647d0.json"
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        jsonf, scope)
    gc = gspread.authorize(credentials)
    today_str = datetime.strftime(today, '%Y-%m-%d')
    old_day_str = datetime.strftime(old_day, '%Y-%m-%d')

    sh = gc.open_by_key(config.SPREADSHEET_KEY)
    worksheet_list = sh.worksheets()
    for worksheet in worksheet_list:
        if (worksheet.title == today_str):
            sh.del_worksheet(worksheet)
        if (worksheet.title == old_day_str):
            sh.del_worksheet(worksheet)

    sh.add_worksheet(title=today_str, rows=len(data)+1, cols=20)
    worksheet = sh.worksheet(today_str)
    return worksheet

# キーワードチェック
def keyword_check(caption):
    if all(map(caption.__contains__, ("foo", "bar",))):
        return 'OK'
    else:
        return 'NG'

# 投稿日をコンバート
def convert_created_time(timestamp):
    convert_timestamp = timestamp.replace('T', ' ').replace('+0000', '')
    convert_time = datetime.strptime(convert_timestamp, '%Y-%m-%d %H:%M:%S')
    ja_time = convert_time + timedelta(hours=9)
    return ja_time

# 経過時間を計算
def calculate_elapsed_time(created_time):
    now = datetime.now(pytz.timezone('Asia/Tokyo'))
    now_str = now.strftime('%Y-%m-%d %H:%M:%S')
    convert_time_now = datetime.strptime(now_str, '%Y-%m-%d %H:%M:%S')
    elapsed_time = convert_time_now - created_time
    elapsed_time_seconds = elapsed_time.total_seconds()
    elapsed_time_hours = math.floor(elapsed_time_seconds // 3600)
    elapsed_time_str = str(elapsed_time_hours) + '時間'

    if (elapsed_time_hours < 1):
        elapsed_time_str = '1時間未満'

    return elapsed_time_str

# SSのCellのフォーマット
def update_worksheet(ws, data):
    ws.update_cell(1, 1, '投稿削除')
    ws.update_cell(1, 2, 'キーワード')
    ws.update_cell(1, 3, '経過時間')
    ws.update_cell(1, 4, '投稿時間')
    ws.update_cell(1, 5, '投稿者')
    ws.update_cell(1, 6, 'フォロワー数')
    ws.update_cell(1, 7, 'いいね数')
    ws.update_cell(1, 8, 'コメント数')
    ws.update_cell(1, 9, 'URL')
    ws.update_cell(1, 10, 'CVR')
    ws.update_cell(1, 11, '成約結果')

    # Color RGB (a/255, b/255, c/255)
    blue_format = CellFormat(
        backgroundColor=Color(0, 0, 1),
        textFormat=TextFormat(bold=True, foregroundColor=Color(1, 1, 1)),
    )
    red_format = CellFormat(
        backgroundColor=Color(1, 0, 0),
        textFormat=TextFormat(bold=True, foregroundColor=Color(1, 1, 1)),
    )
    green_format = CellFormat(
        backgroundColor=Color(0, 0.5, 0),
        textFormat=TextFormat(bold=True, foregroundColor=Color(1, 1, 1)),
    )
    all_format = CellFormat(horizontalAlignment='CENTER')

    set_column_width(ws, created_time_column, 150)
    set_column_width(ws, permalink_column, 300)
    format_cell_range(ws, 'A1:I1', blue_format)
    format_cell_range(ws, 'J1', red_format)
    format_cell_range(ws, 'K1', green_format)
    format_cell_range(ws, '1:' + str(len(data)+1), all_format)

# SSにデータ書き込み
def write_data(ws, data):
    i = 2
    for d in data:
        keyword_result = keyword_check(d['caption'])
        created_ja_time = convert_created_time(d['timestamp'])
        created_time = created_ja_time.strftime('%Y/%m/%d %H:%M:%S')
        elapsed_time = calculate_elapsed_time(created_ja_time)
        user_name = get_user_name(d['permalink'])
        print(user_name)
        follower_count = get_follower_count(user_name)
        print(follower_count)

        ws.update_acell(delete_post_column + str(i), 'OK')
        ws.update_acell(keyword_column + str(i), keyword_result)
        ws.update_acell(elapsed_time_column + str(i), elapsed_time)
        ws.update_acell(created_time_column + str(i), created_time)
        ws.update_acell(user_name_column + str(i), user_name)
        ws.update_acell(follower_count_column + str(i), follower_count)
        ws.update_acell(like_count_column + str(i), d['like_count'])
        ws.update_acell(comment_count_column + str(i), d['comments_count'])
        ws.update_acell(permalink_column + str(i), d['permalink'])
        i += 1

# 昨日の投稿で削除済みのものがないかチェック
def check_if_yesterday_post_exists():
    today = datetime.today()
    yesterday = today - timedelta(days=1)
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    jsonf = "instagram-for-influencer-d2613e5647d0.json"
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        jsonf, scope)
    gc = gspread.authorize(credentials)
    yesterday_str = datetime.strftime(yesterday, '%Y-%m-%d')

    sh = gc.open_by_key(config.SPREADSHEET_KEY)
    worksheet = sh.worksheet(yesterday_str)
    post_column = worksheet.row_count + 1
    for i in range(2, post_column):
        permalink = worksheet.acell(permalink_column + str(i)).value
        # StatusCode 429を避ける => headers={'User-agent': 'your bot 0.1'}
        response = requests.get(permalink,headers={'User-agent': 'your bot 0.1'})
        print(response.status_code)
        if (response.status_code != 200):
            worksheet.update_acell(delete_post_column + str(i), 'NG')


def getPosts(event, context):
    settingDriver()
    response = requests.get(f'https://graph.facebook.com/v9.0/{config.NODE_ID}/recent_media?user_id={config.USER_ID}&fields=media_url,media_type,comments_count,id,like_count,permalink,caption,timestamp&access_token={config.ACCESS_TOKEN}')
    data = response.json()['data']
    ws = create_worksheet(data)
    update_worksheet(ws, data)
    write_data(ws, data)
    check_if_yesterday_post_exists()
