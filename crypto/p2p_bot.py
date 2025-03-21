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

VERBOSE = True  # Toggle console logging

def log(message):
    if VERBOSE:
        print(message)

# Discord webhook URL
DISCORD_WEBHOOK_URL = 'https://discord.com/api/webhooks/1328688743808503900/2yPZeM8nat3A6bd4WdYPzhT0atu0K_jgPvixsMUhFe_C_liyF3cphscOGUXkp_3LRGhT'

# Path to your ChromeDriver
CHROMEDRIVER_PATH = '../drivers/chromedriver.exe'

# Binance P2P URLs (PGK to USDT)
BINANCE_URL1 = 'https://p2p.binance.com/trade/sell/USDT?fiat=PGK&payment=all-payments'
BINANCE_URL2 = 'https://p2p.binance.com/trade/all-payments/USDT?fiat=PGK'

# Bybit OTC URLs (MYR to USDT)
BYBIT_BUY_URL = 'https://www.bybit.com/en/fiat/trade/otc/buy/USDT/MYR'
BYBIT_SELL_URL = 'https://www.bybit.com/en/fiat/trade/otc/sell/USDT/MYR'
BUYER_WHITELIST = ["Bernice", "Fast Trader 88", "zspeed", "凯凯交易", "Jc1033", "Cryptgod", "UPCRYPT", "Good Day888", "AlphaFast", "Kai Trader 888"]

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

# Global variables to track alerts
alerts_sent = set()  # Holds thresholds that have been alerted for the day
last_reset_date = None  # To help reset alerts each day after 08:00

# ----------------------------- Helper Functions -----------------------------

def send_discord_message(message):
    """Sends a message to the configured Discord webhook."""
    data = {"content": message}
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=data)
        if response.status_code == 204:
            log("Message sent to Discord successfully!")
        else:
            log(f"Failed to send message to Discord: {response.status_code} - {response.text}")
    except Exception as e:
        log(f"Exception while sending Discord message: {e}")

def reset_alerts():
    """Resets the daily alerts after 08:00 if a new day has started."""
    global alerts_sent, last_reset_date
    now = datetime.now()
    current_date = now.date()
    if last_reset_date != current_date and now.hour >= 8:
        alerts_sent.clear()
        last_reset_date = current_date
        log("Alerts reset for the new day.")

def create_chrome_driver():
    """Creates and returns a Selenium Chrome driver instance with desired options."""
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
    return driver

# ----------------------------- Rate Extraction Functions -----------------------------

def get_rate_binance(url):
    """
    Retrieves the exchange rate from a Binance P2P page.
    Returns the rate as a float, or None on failure.
    """
    log(f"Navigating to {url}")
    driver = create_chrome_driver()
    try:
        driver.get(url)
        log("Waiting for 10 seconds to allow the page to load...")
        time.sleep(10)
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

def get_rate_bybit(url, whitelist=None):
    """
    Retrieves the price from a Bybit OTC page.
    If a whitelist is provided (for BUY), only rows with approved advertisers are considered.
    Returns the price as a float, or None on failure.
    """
    log(f"Navigating to {url}")
    driver = create_chrome_driver()
    try:
        driver.get(url)
        log("Waiting for 10 seconds to allow the page to load...")
        time.sleep(10)
        rows = WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located(
                (By.XPATH, "//tbody[contains(@class, 'trade-table__tbody')]/tr[not(contains(@class, 'new-user-ads'))]")
            )
        )
        for row in rows:
            if whitelist:
                try:
                    buyer_element = row.find_element(By.XPATH, ".//div[contains(@class, 'advertiser-name')]/span")
                    buyer_name = buyer_element.text.strip()
                    log(f"Found advertiser: {buyer_name}")
                except Exception as e:
                    log(f"Could not extract buyer name from row: {e}")
                    continue
                if buyer_name not in whitelist:
                    log(f"Advertiser '{buyer_name}' is not in whitelist. Skipping row.")
                    continue
            try:
                price_element = row.find_element(By.XPATH, "./td[2]//span[1]")
                price_text = price_element.text.strip().replace("MYR", "").strip()
                log(f"Extracted price text: {price_text}")
                price = float(price_text.replace(',', ''))
                log(f"Converted price: {price} MYR")
                return price
            except Exception as e:
                log(f"Error extracting price from the row: {e}")
                continue
        log("No valid row found matching criteria.")
        return None
    except Exception as e:
        log(f"Error extracting price from {url}: {e}")
        return None
    finally:
        driver.quit()

# ----------------------------- Spread Check Functions -----------------------------

def check_binance_spread():
    """
    Checks the Binance P2P rates and computes the spread percentage.
    Returns a tuple (spread_percentage, rate1, rate2) or None on failure.
    """
    rate1 = get_rate_binance(BINANCE_URL1)
    rate2 = get_rate_binance(BINANCE_URL2)
    if rate1 is None or rate2 is None:
        log("Failed to extract one or both Binance rates. Skipping Binance check.")
        return None
    spread_percentage = ((rate1 - rate2) / rate2) * 100
    log(f"Binance: Rate1: {rate1} PGK, Rate2: {rate2} PGK, Spread: {spread_percentage:.2f}%")
    return spread_percentage, rate1, rate2

def check_bybit_spread():
    """
    Checks the Bybit OTC rates and computes the spread percentage.
    Returns a tuple (spread_percentage, rate_buy, rate_sell) or None on failure.
    """
    rate_buy = get_rate_bybit(BYBIT_BUY_URL, whitelist=BUYER_WHITELIST)
    rate_sell = get_rate_bybit(BYBIT_SELL_URL)
    if rate_buy is None or rate_sell is None:
        log("Failed to extract one or both Bybit rates. Skipping Bybit check.")
        return None
    spread_percentage = ((rate_sell - rate_buy) / rate_buy) * 100
    log(f"Bybit: Buy Price: {rate_buy} MYR, Sell Price: {rate_sell} MYR, Spread: {spread_percentage:.2f}%")
    return spread_percentage, rate_buy, rate_sell

def process_alerts(source, spread, details):
    """
    Processes alerts for a given source (Binance or Bybit) if the spread exceeds the next threshold.
    Uses the shared global alerts_sent set so that alerts from one market affect the other.
    """
    global alerts_sent
    new_thresholds = [thr for (thr, amt) in SELL_THRESHOLDS if spread >= thr and thr not in alerts_sent]
    if new_thresholds:
        highest_new_threshold = max(new_thresholds)
        tranche_sell = next(amt for (thr, amt) in SELL_THRESHOLDS if thr == highest_new_threshold)
        cumulative_sell = sum(amt for (thr, amt) in SELL_THRESHOLDS if thr <= highest_new_threshold)
        message = (
            f"Alert! {source} spread detected.\n"
            f"{details}\n"
            f"Spread: {spread:.2f}%\n"
            f"New threshold reached: {highest_new_threshold}%\n"
            f"Tranche sell: {tranche_sell}, Cumulative sell: {cumulative_sell}"
        )
        send_discord_message(message)
        # Mark thresholds up to the highest_new_threshold as alerted.
        for thr, amt in SELL_THRESHOLDS:
            if thr <= highest_new_threshold:
                alerts_sent.add(thr)
    else:
        log(f"{source}: Spread below new alert thresholds or already alerted.")

# ----------------------------- Main Loop -----------------------------

def main():
    log("Starting combined exchange rate monitor...")
    while True:
        reset_alerts()

        # --- Binance Check ---
        binance_result = check_binance_spread()
        if binance_result:
            binance_spread, rate1, rate2 = binance_result
            details = f"Binance Rates: {rate1} PGK (URL1) vs {rate2} PGK (URL2)"
            process_alerts("Binance", binance_spread, details)
        else:
            log("Binance check skipped due to rate extraction failure.")

        # --- Bybit Check ---
        bybit_result = check_bybit_spread()
        if bybit_result:
            bybit_spread, rate_buy, rate_sell = bybit_result
            details = f"Bybit Rates: Buy: {rate_buy} MYR, Sell: {rate_sell} MYR"
            process_alerts("Bybit", bybit_spread, details)
        else:
            log("Bybit check skipped due to rate extraction failure.")

        log("Waiting for 60 seconds before the next iteration...\n")
        time.sleep(60)

if __name__ == "__main__":
    main()
