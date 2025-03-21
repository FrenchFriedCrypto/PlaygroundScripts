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


# Set your Discord webhook URL
DISCORD_WEBHOOK_URL = 'https://discord.com/api/webhooks/1328688743808503900/2yPZeM8nat3A6bd4WdYPzhT0atu0K_jgPvixsMUhFe_C_liyF3cphscOGUXkp_3LRGhT'

# Path to your ChromeDriver
CHROMEDRIVER_PATH = '../../drivers/chromedriver.exe'

# Define the Bybit OTC SELL URL
BYBIT_SELL_URL = 'https://www.bybit.com/en/fiat/trade/otc/sell/USDT/MYR'

# Threshold for sending alert
SELL_THRESHOLD = 4.6



# ----------------------------- Functions -----------------------------

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


def get_rate_bybit(url, whitelist=None):
    """
    Retrieves the price from the Bybit OTC table.
    This function ignores any <tr> element with a class containing 'new-user-ads'.

    If a whitelist is provided, it will only consider rows where the advertiser's name
    is in the whitelist. For our sell side monitoring, we won't be using a whitelist.
    Returns the price from the first matching row.

    Args:
        url (str): The Bybit OTC URL.
        whitelist (list, optional): List of advertiser names to allow. Default is None.

    Returns:
        float or None: The extracted price, or None if extraction fails.
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
        time.sleep(10)

        log("Locating table rows (ignoring rows with 'new-user-ads')...")
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
                    log(f"Could not extract advertiser name from row: {e}")
                    continue

                if buyer_name not in whitelist:
                    log(f"Advertiser '{buyer_name}' is not in whitelist. Skipping row.")
                    continue

            try:
                # Extract the price from the second <td> element (Price column).
                price_element = row.find_element(By.XPATH, "./td[2]//span[1]")
                price_text = price_element.text.strip()
                price_text = price_text.replace("MYR", "").strip()
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


def monitor_sell_side():
    """
    Continuously monitors the Bybit OTC sell rates.
    Sends a Discord alert if an order is found with a price of 4.6 MYR or higher.
    """
    log("Starting Sell side order monitor...")
    while True:
        try:
            sell_price = get_rate_bybit(BYBIT_SELL_URL)
            if sell_price is None:
                log("Failed to extract sell price.")
            else:
                log(f"Sell Price: {sell_price} MYR per USDT")
                if sell_price >= SELL_THRESHOLD:
                    message = (
                        f"Alert! Sell order detected with price {sell_price} MYR per USDT, "
                        f"which meets/exceeds the threshold of {SELL_THRESHOLD}."
                    )
                    send_discord_message(message)
                else:
                    log("Sell price is below the threshold.")
        except Exception as e:
            log(f"An error occurred in the monitoring loop: {e}")

        log("Waiting for 20 seconds before the next check...\n")
        time.sleep(20)


# ----------------------------- Main Execution -----------------------------
if __name__ == "__main__":
    monitor_sell_side()
