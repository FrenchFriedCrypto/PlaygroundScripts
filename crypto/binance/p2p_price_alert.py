import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ----------------------------- Configuration -----------------------------

# Set your Discord webhook URL
# 🔒 **Important:** Replace this URL with your actual Discord webhook URL.
DISCORD_WEBHOOK_URL = 'https://discord.com/api/webhooks/1328688743808503900/2yPZeM8nat3A6bd4WdYPzhT0atu0K_jgPvixsMUhFe_C_liyF3cphscOGUXkp_3LRGhT'

# Path to your ChromeDriver
# 📂 **Note:** Ensure the path is correct. If ChromeDriver is in your system PATH, you can use 'chromedriver' instead.
CHROMEDRIVER_PATH = '../../drivers/chromedriver.exe'  # Replace with your actual path if different


# ----------------------------- Functions -----------------------------

def send_discord_message(message):
    """
    Sends a message to the configured Discord webhook.

    Args:
        message (str): The message content to send.

    What Can Be Changed:
        - The structure of the `data` dictionary (e.g., adding embeds).
        - Error handling or logging mechanisms.

    What Cannot Be Changed:
        - The `DISCORD_WEBHOOK_URL` must remain correctly formatted for Discord to accept the message.
    """
    data = {
        "content": message
    }
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=data)
        if response.status_code == 204:
            print("✅ Message sent to Discord successfully!")
        else:
            print(f"❌ Failed to send message to Discord: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Exception while sending Discord message: {e}")


def get_pgk_to_usdt_rate():
    """
    Retrieves the first (lowest) PGK to USDT exchange rate from Binance P2P using Selenium.

    Returns:
        float or None: The extracted exchange rate, or None if extraction fails.

    What Can Be Changed:
        - The `url` if Binance changes their P2P trading page structure.
        - Selenium options (e.g., headless mode, window size).
        - The CSS selector used to locate the price element.
        - The sleep duration or WebDriverWait timeout based on page load times.

    What Cannot Be Changed:
        - The fundamental logic to navigate to the Binance P2P page and extract the exchange rate.
    """
    url = 'https://p2p.binance.com/en/trade/sell/USDT?fiat=PGK&payment=all-payments'
    print(f"🔍 Navigating to {url}")

    # Set up Selenium options
    chrome_options = Options()
    chrome_options.add_argument(
        "--headless")  # 🛑 **Note:** Running in headless mode means no browser window will appear.
    chrome_options.add_argument("--disable-gpu")  # Disables GPU usage; useful for headless environments.
    chrome_options.add_argument("--no-sandbox")  # Bypass OS security model; necessary in some environments.
    chrome_options.add_argument("--window-size=1920,1080")  # Sets the window size; can be adjusted as needed.

    # Optional: Set a user-agent to mimic a real browser
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    )

    # Initialize the WebDriver
    # 🔒 **Important:** Ensure that `CHROMEDRIVER_PATH` points to a valid ChromeDriver executable compatible with your Chrome version.
    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get(url)

        # Wait for the page to load completely
        print("⌛ Waiting for 10 seconds to allow the page to load...")
        time.sleep(10)  # 🕒 **Note:** This is a fixed wait; consider using dynamic waits for better efficiency.

        # Attempt to locate the exchange rate element using the updated CSS selector
        print("⌛ Attempting to locate the exchange rate element...")
        price_element = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.headline5.mr-4xs.text-primaryText'))
        )

        # Extract the price text
        price_text = price_element.text.strip()
        print(f"💰 Extracted Price Text: {price_text} PGK")

        # Remove any non-numeric characters (like commas) and convert to float
        price = float(price_text.replace(',', ''))
        print(f"📈 Converted Price: {price} PGK")
        return price

    except Exception as e:
        print(f"❗ Error extracting price: {e}")
        return None
    finally:
        driver.quit()  # 🛑 **Important:** Ensures that the browser is closed regardless of success or failure.


def monitor_exchange_rate(threshold):
    """
    Continuously monitors the PGK to USDT exchange rate and sends a Discord alert when the rate rises above the threshold.

    Args:
        threshold (float): The exchange rate threshold to trigger an alert.

    What Can Be Changed:
        - The `threshold` value to set different alert points.
        - The `time.sleep` duration to adjust the monitoring frequency.
        - The structure and content of the alert message.

    What Cannot Be Changed:
        - The core monitoring loop logic.
    """
    print(f"🚀 Starting exchange rate monitor with threshold: {threshold} PGK")
    while True:
        try:
            rate = get_pgk_to_usdt_rate()
            if rate is not None:
                print(f"📊 Current rate: {rate} PGK per USDT")
                if rate > threshold:
                    # 📢 **Alert:** Notify when the rate rises above the threshold
                    message = (
                        f"📈 **Alert!**\n"
                        f"PGK to USDT exchange rate has risen above {threshold}: "
                        f"Current rate is {rate} PGK per USDT."
                    )
                    send_discord_message(message)
                else:
                    print(f"✅ No action needed. The rate is below the threshold of {threshold} PGK.")
            else:
                print("⚠️ Rate is None, unable to proceed.")
        except Exception as e:
            print(f"❌ An error occurred: {e}")

        # Wait before checking again
        print("⏳ Waiting for 60 seconds before the next check...\n")
        time.sleep(60)  # 🕒 **Note:** Adjusted sleep duration to match the print statement


# ----------------------------- Main Execution -----------------------------

if __name__ == "__main__":
    # Set your desired threshold rate here
    threshold_rate = 4.546  # 💡 **Tip:** Adjust this value based on your monitoring needs
    monitor_exchange_rate(threshold_rate)
