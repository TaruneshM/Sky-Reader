from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

options = Options()
options.add_argument('--headless=new')
options.add_argument('--window-size=1440,960')
options.add_argument('--disable-gpu')
driver = webdriver.Chrome(options=options)

try:
    driver.get('http://127.0.0.1:5173')
    time.sleep(1)
    driver.execute_script("""
        localStorage.setItem('skyreader_token', 'iQ2LQeRTCigSB2PS83ejqmX2srgB6x1asqj3a9ZxRgk');
        localStorage.setItem('skyreader_atmosphere_mode', 'auto');
    """)
    driver.get('http://127.0.0.1:5173')
    time.sleep(2)

    # Click chat
    chat_btns = driver.find_elements(By.XPATH, "//span[contains(text(), 'Chat')]/..")
    if chat_btns:
        chat_btns[0].click()
        time.sleep(1)

    inputs = driver.find_elements(By.CSS_SELECTOR, "textarea, input[type='text']")
    if inputs:
        inp = inputs[-1]
        inp.send_keys("What is the current weather in Lisbon?")
        inp.send_keys(Keys.ENTER)
        time.sleep(5)

    # Click audit button
    toggle_btns = driver.find_elements(By.CLASS_NAME, "audit-toggle-btn")
    print(f"Found {len(toggle_btns)} audit toggle buttons")
    if toggle_btns:
        driver.execute_script("arguments[0].click();", toggle_btns[-1])
        time.sleep(2)
        driver.save_screenshot('C:/Users/upret/Desktop/sk/Sky-Reader/report_assets/fig_audit_drawer.png')
        print("Captured fig_audit_drawer.png successfully!")
    else:
        print("No toggle button found!")

finally:
    driver.quit()
