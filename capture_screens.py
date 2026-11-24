from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

options = Options()
options.add_argument('--headless=new')
options.add_argument('--window-size=1440,920')
options.add_argument('--disable-gpu')
driver = webdriver.Chrome(options=options)

try:
    # 1. Login with session token
    driver.get('http://127.0.0.1:5173')
    time.sleep(1)
    driver.execute_script("""
        localStorage.setItem('skyreader_token', 'iQ2LQeRTCigSB2PS83ejqmX2srgB6x1asqj3a9ZxRgk');
        localStorage.setItem('skyreader_atmosphere_mode', 'auto');
    """)
    driver.get('http://127.0.0.1:5173')
    time.sleep(3)

    # 2. Capture City Lookup (Dashboard & Trips)
    lookup_btns = driver.find_elements(By.XPATH, "//span[contains(text(), 'Dashboard & Trips')]/..")
    if lookup_btns:
        lookup_btns[0].click()
        time.sleep(3)
        driver.save_screenshot('C:/Users/upret/Desktop/sk/Sky-Reader/report_assets/fig_city_lookup.png')
        print('Captured fig_city_lookup.png')

    # 3. Switch back to Chat
    chat_btns = driver.find_elements(By.XPATH, "//span[contains(text(), 'Chat')]/..")
    if chat_btns:
        chat_btns[0].click()
        time.sleep(1)

    # Send a weather query
    inputs = driver.find_elements(By.CSS_SELECTOR, "textarea, input[type='text']")
    if inputs:
        inp = inputs[-1]
        inp.send_keys("Compare the weather in Lisbon and Madrid")
        inp.send_keys(Keys.ENTER)
        print("Sent chat message, waiting for response...")
        time.sleep(6)
        driver.save_screenshot('C:/Users/upret/Desktop/sk/Sky-Reader/report_assets/fig_chat_conversation.png')
        print('Captured fig_chat_conversation.png')

        # Look for buttons to inspect claims/audit/evidence
        audit_btns = driver.find_elements(By.XPATH, "//button[contains(., 'Audit') or contains(., 'Evidence') or contains(., 'Proof') or contains(., 'Claims') or contains(., 'audit')]")
        if audit_btns:
            print(f"Found {len(audit_btns)} audit buttons, clicking first...")
            driver.execute_script("arguments[0].click();", audit_btns[0])
            time.sleep(2)
            driver.save_screenshot('C:/Users/upret/Desktop/sk/Sky-Reader/report_assets/fig_audit_drawer.png')
            print('Captured fig_audit_drawer.png')
        else:
            print("No audit button found directly")

    # 4. Preferences View
    pref_btns = driver.find_elements(By.XPATH, "//span[contains(text(), 'Preferences')]/..")
    if pref_btns:
        pref_btns[0].click()
        time.sleep(2)
        driver.save_screenshot('C:/Users/upret/Desktop/sk/Sky-Reader/report_assets/fig_preferences.png')
        print('Captured fig_preferences.png')

except Exception as e:
    print("Error:", e)
finally:
    driver.quit()
