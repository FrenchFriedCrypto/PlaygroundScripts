import time
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ----------------------------- Configuration -----------------------------

# Toggle for printing log statements. Set to True to enable printing, False to disable.
VERBOSE = True

def log(message):
    if VERBOSE:
        print(message)

# Set your Discord webhook URL
DISCORD_WEBHOOK_URL = 'https://discord.com/api/webhooks/1328688743808503900/2yPZeM8nat3A6bd4WdYPzhT0atu0K_jgPvixsMUhFe_C_liyF3cphscOGUXkp_3LRGhT'

# Path to your ChromeDriver
CHROMEDRIVER_PATH = '../../drivers/chromedriver.exe'

# Define the two Binance P2P URLs
URL1 = 'https://p2p.binance.com/trade/sell/USDT?fiat=PGK&payment=all-payments'
URL2 = 'https://p2p.binance.com/trade/all-payments/USDT?fiat=PGK'

# ----------------------------- Threshold Settings -----------------------------
# List of tuples: (spread_threshold_in_percent, sell_amount)
SELL_THRESHOLDS = [
    (1.60, 15000),
    (1.80, 5000),
    (2.00, 10000),
    (2.20, 5000),
    (2.50, 5000),
    (2.80, 5000),
    (3.00, 5000)
]

# ----------------------------- Functions -----------------------------

def send_discord_message(message):
    """
    Sends a message to the configured Discord webhook.
    """
    data = {"content": message}
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=data)
        if response.status_code == 204:
            log("Message sent to Discord successfully!")
        else:
            log(f"Failed to send message to Discord: {response.status_code} - {response.text}")
    except Exception as e:
        log(f"Exception while sending Discord message: {e}")

def get_rate(url):
    """
    Retrieves the first (best) PGK to USDT exchange rate from the given Binance P2P URL using Selenium.

    Args:
        url (str): The Binance P2P URL to scrape.

    Returns:
        float or None: The extracted exchange rate, or None if extraction fails.
    """
    log(f"Navigating to {url}")

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    )

    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get(url)
        log("Waiting for 10 seconds to allow the page to load...")
        time.sleep(10)  # Consider using dynamic waits if possible.
        log("Attempting to locate the exchange rate element...")
        price_element = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.headline5.mr-4xs.text-primaryText'))
        )
        price_text = price_element.text.strip()
        log(f"Extracted Price Text: {price_text} PGK")
        price = float(price_text.replace(',', ''))
        log(f"Converted Price: {price} PGK")
        return price
    except Exception as e:
        log(f"Error extracting price from {url}: {e}")
        return None
    finally:
        driver.quit()

def monitor_exchange_rate():
    """
    Continuously monitors the PGK to USDT exchange rates from two URLs and sends a Discord alert
    if the percentage spread between URL2 and URL1 exceeds your defined thresholds.

    An alert for a given tranche (threshold) is only sent once per day.
    Alerts are reset every day at 08:00.
    """
    alerts_sent = set()  # Set to track thresholds alerted for the current day.
    last_reset_date = None

    log("Starting exchange rate monitor...")
    while True:
        now = datetime.now()
        current_date = now.date()
        # Reset alerts if it's after 08:00 and we haven't reset for today.
        if last_reset_date != current_date and now.hour >= 8:
            alerts_sent.clear()
            last_reset_date = current_date
            log("Alerts reset for the new day.")

        try:
            rate1 = get_rate(URL1)
            rate2 = get_rate(URL2)
            if rate1 is None or rate2 is None:
                log("Failed to extract one or both rates. Skipping this iteration.")
            else:
                # Calculate the spread as a percentage.
                spread_percentage = ((rate1 - rate2) / rate2) * 100
                log(f"Rate1: {rate1} PGK, Rate2: {rate2} PGK, Spread: {spread_percentage:.2f}%")

                # Determine which thresholds have been reached but not yet alerted.
                new_thresholds = [thr for (thr, amt) in SELL_THRESHOLDS if
                                  spread_percentage >= thr and thr not in alerts_sent]

                if new_thresholds:
                    # Choose the highest new threshold reached.
                    highest_new_threshold = max(new_thresholds)
                    tranche_sell = next(amt for (thr, amt) in SELL_THRESHOLDS if thr == highest_new_threshold)
                    # Cumulative sell is the sum of sell amounts for all thresholds up to the highest_new_threshold.
                    cumulative_sell = sum(amt for (thr, amt) in SELL_THRESHOLDS if thr <= highest_new_threshold)

                    message = (
                        f"Alert! PGK to USDT spread detected.\n"
                        f"Rate1: {rate1} PGK per USDT\n"
                        f"Rate2: {rate2} PGK per USDT\n"
                        f"Spread: {spread_percentage:.2f}%\n"
                        f"New threshold reached: {highest_new_threshold}%\n"
                        f"Tranche sell: {tranche_sell}, Cumulative sell: {cumulative_sell}"
                    )
                    send_discord_message(message)

                    # Mark all thresholds up to the highest_new_threshold as alerted.
                    for thr, amt in SELL_THRESHOLDS:
                        if thr <= highest_new_threshold:
                            alerts_sent.add(thr)
                else:
                    log("Spread below new alert thresholds or already alerted for this day.")
        except Exception as e:
            log(f"An error occurred in the monitoring loop: {e}")

        log("Waiting for 60 seconds before the next check...\n")
        time.sleep(60)

# ----------------------------- Main Execution -----------------------------

if __name__ == "__main__":
    monitor_exchange_rate()
