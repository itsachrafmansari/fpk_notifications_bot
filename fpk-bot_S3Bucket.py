import json
import os
import time
import boto3
import telegram
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def lambda_handler(_event, _context):
    url1 = os.getenv('URL1')
    url2 = os.getenv('URL2')
    try:
        college_website_response = requests.get(url1, timeout=6).status_code
        if college_website_response == 200:
            # ████████████████████████████████████████████ S3 BUCKET 1 ████████████████████████████████████████████
            s3 = boto3.client('s3')
            bucket = os.getenv('BUKCET_NAME')
            storage_file = os.getenv('STORAGE_FILE')
            new_announcements = {}
            old_announcements = json.loads(
            s3.get_object(Bucket=bucket, Key=storage_file)["Body"].read().decode('utf-8'))

            # ████████████████████████████████████████████ WEB SCRAPPING ████████████████████████████████████████████
            # Setup the web scrapper -------------------------------------------------
            options = Options()
            options.binary_location = '/opt/headless-chromium'
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--single-process')
            options.add_argument('--disable-dev-shm-usage')

            web_page = webdriver.Chrome('/opt/chromedriver', chrome_options=options)

            # Scrap all the current announcments from the website -------------------------------------------------
            current_announcements = {}

            web_page1 = webdriver.Chrome('/opt/chromedriver', chrome_options=options)
            web_page1.get(url1)
            table = web_page1.find_element_by_tag_name('tbody').find_elements_by_tag_name("tr")
            for row in table:
                col = row.find_element_by_tag_name('td')

                lien = col.find_element_by_tag_name('a').get_attribute('href').replace("index.php/", "")
                titre = str(col.find_elements_by_tag_name("a")[0].text)
                date = str(col.text).replace(titre, "").replace("\n>> Lire la suite", "").replace(" -", "")

                # Storing the current announcements in a list
                current_announcements[lien] = {
                    'titre': titre,
                    'date': date
                }
            web_page1.close()
            web_page1.quit()

            web_page2 = webdriver.Chrome('/opt/chromedriver', chrome_options=options)
            web_page.get(url2)
            table = web_page.find_element_by_tag_name('tbody').find_elements_by_tag_name("tr")
            for row in table:
                cols = row.find_elements_by_tag_name('td')

                date = cols[0].text
                titre = cols[1].find_element_by_tag_name('a').text
                lien = cols[1].find_element_by_tag_name('a').get_attribute('href').replace("index.php/", "")

                # Storing the current announcements in a list
                if lien not in current_announcements:
                    current_announcements[lien] = {
                        'titre': titre,
                        'date': date
                    }
            web_page2.close()
            web_page2.quit()

            # ████████████████████████████████████████████ S3 BUCkET 2 ████████████████████████████████████████████
            for current_announcement in current_announcements:
                if current_announcement.replace("index.php/", "") not in {**old_announcements, **new_announcements}:
                    new_announcements[current_announcement.replace("index.php/", "")] = {
                        'titre': current_announcements[current_announcement]['titre'],
                        'date': current_announcements[current_announcement]['date'],
                    }

            if len(new_announcements) > 0:
                current_announcements_json = bytes(json.dumps(current_announcements).encode("UTF-8"))
                s3.put_object(Bucket=bucket, Key=storage_file, Body=current_announcements_json)

                # ████████████████████████████████████████████ BOT ████████████████████████████████████████████
                bot_token = os.getenv('TELEGRAM_TOKEN')
                bot = telegram.Bot(bot_token)
                chat_id = -int(os.getenv('TELEGRAM_CHAT_ID_TEST'))

                def send_message(chat_id, message_content):
                    # Check that token is not empty
                    if bot_token is not None:
                        bot.send_message(text=message_content, chat_id=chat_id, parse_mode=telegram.ParseMode.HTML)
                    else:
                        raise EnvironmentError("Missing TELEGRAM_TOKEN env variable!")

                for announcement in new_announcements:
                    message = f'''<a href="{announcement}">{new_announcements[announcement]['titre']}</a>\n\nDate : {new_announcements[announcement]['date']}\n\n'''
                    send_message(chat_id, message)
                    time.sleep(3)

            return "████████████████████████████████████████████ SUCCESS ████████████████████████████████████████████"
    except requests.exceptions.Timeout:
        return "XXXXXXXXXXXXXXXXXX COLLEGE WEBSITE IS DOWN XXXXXXXXXXXXXXXXXX"
