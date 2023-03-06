import json
import os
import time
import boto3
import telegram
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def lambda_handler(_event, _context):

    # Environment Variables
    url1 = os.getenv('URL1')
    bucket = os.getenv('BUCKET_NAME')
    storage_file = os.getenv('STORAGE_FILE')
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    TELEGRAM_CHAT_ID_TEST = os.getenv('TELEGRAM_CHAT_ID_TEST')

    if TELEGRAM_TOKEN is None:
        raise EnvironmentError("XXXXXXXXXXXXXXXXXX Missing TELEGRAM_TOKEN env variable! XXXXXXXXXXXXXXXXXX")

    try:
        college_website_response = requests.get(url1, timeout=6).status_code
        if college_website_response == 200:
            # ████████████████████████████████████████████ S3 BUCKET 1 ████████████████████████████████████████████
            s3 = boto3.client('s3')
            old_announcements = json.loads(
                s3.get_object(Bucket=bucket, Key=storage_file)["Body"].read().decode('utf-8')
            )

            # ████████████████████████████████████████████ WEB SCRAPPING ████████████████████████████████████████████
            # Setup the web scrapper -------------------------------------------------
            options = Options()
            options.binary_location = '/opt/headless-chromium'
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--single-process')
            options.add_argument('--disable-dev-shm-usage')
            web_page = webdriver.Chrome('/opt/chromedriver', chrome_options=options)
            web_page.get(url1)

            # Scrap all the current announcements from the website -------------------------------------------------
            current_announcements = {}

            articles = web_page.find_element_by_id("main").find_elements_by_tag_name("article")
            for article in articles:

                # Extract the title and link
                header = article.find_element_by_tag_name('header')
                h2 = header.find_element_by_tag_name('h2')
                a_link1 = h2.find_element_by_tag_name("a")
                link = a_link1.get_attribute('href')
                title = a_link1.text

                # Extract the date
                div_entry_meta = header.find_element_by_tag_name("div")
                span = div_entry_meta.find_element_by_tag_name("span")
                a_link2 = span.find_element_by_tag_name("a")
                date = a_link2.find_element_by_tag_name("time").text

                # Storing the current announcements in a list
                current_announcements[link] = {
                    'titre': title,
                    'date': date
                }

            web_page.close()
            web_page.quit()

            # ████████████████████████████████████████████ S3 BUCkET 2 ████████████████████████████████████████████
            new_announcements = {}
            for announcement_link in current_announcements:
                if announcement_link not in {**old_announcements, **new_announcements}:

                    # Add any new announcement to the new_announcements dictionary
                    new_announcements[announcement_link] = {
                        'titre': current_announcements[announcement_link]['titre'],
                        'date': current_announcements[announcement_link]['date'],
                    }

            if len(new_announcements) > 0:
                current_announcements_json = bytes(json.dumps(current_announcements).encode("UTF-8"))
                s3.put_object(Bucket=bucket, Key=storage_file, Body=current_announcements_json)

                # ████████████████████████████████████████████ BOT ████████████████████████████████████████████

                bot = telegram.Bot(TELEGRAM_TOKEN)
                chat_id = -int(TELEGRAM_CHAT_ID_TEST)

                for announcement in new_announcements:
                    message = f'''<a href="{announcement}">{new_announcements[announcement]['titre']}</a>\n\nDate : {new_announcements[announcement]['date']}\n\n'''
                    bot.send_message(text=message, chat_id=chat_id, parse_mode=telegram.ParseMode.HTML)
                    time.sleep(3)

            return "████████████████████████████████████████████ SUCCESS ████████████████████████████████████████████"

    except requests.exceptions.Timeout:
        return "XXXXXXXXXXXXXXXXXX COLLEGE WEBSITE IS DOWN XXXXXXXXXXXXXXXXXX"
