# pterodactyl_login_with_cookies.py
import os
import json
import time
import getpass
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options

PANEL_URL = "https://panel.hostmybot.net/auth/login"
COOKIES_PATH = "cookies.json"

# Bạn có thể đặt chrome_user_data_dir để dùng profile chrome đã login
chrome_user_data_dir = None  # ví dụ: r"C:\Users\You\AppData\Local\Google\Chrome\User Data"

def try_find(driver, selectors):
    for by, sel in selectors:
        try:
            el = driver.find_element(by, sel)
            return el
        except NoSuchElementException:
            continue
    return None

def save_cookies(driver, path=COOKIES_PATH):
    try:
        cookies = driver.get_cookies()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cookies, f)
        print(f"[+] Đã lưu {len(cookies)} cookie vào {path}")
    except Exception as e:
        print("[!] Lỗi khi lưu cookie:", e)

def load_cookies(driver, path=COOKIES_PATH):
    if not os.path.exists(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            cookies = json.load(f)
        # cần mở domain trước khi add cookie
        driver.get("https://panel.hostmybot.net")
        time.sleep(1)
        for c in cookies:
            # Selenium expects cookie dict without 'sameSite' sometimes
            cookie = {k: v for k, v in c.items() if k in ("name", "value", "path", "domain", "secure", "expiry", "httpOnly")}
            try:
                driver.add_cookie(cookie)
            except Exception:
                # thử bỏ domain để selenium tự set
                cookie2 = cookie.copy()
                cookie2.pop("domain", None)
                try:
                    driver.add_cookie(cookie2)
                except Exception:
                    pass
        print(f"[+] Đã nạp cookie từ {path}")
        return True
    except Exception as e:
        print("[!] Lỗi khi nạp cookie:", e)
        return False

def main():
    USERNAME = os.environ.get("PANEL_USER", "").strip()
    PASSWORD = os.environ.get("PANEL_PASS", "").strip()

    if not USERNAME:
        USERNAME = input("Nhập username hoặc email: ").strip()
    if not PASSWORD:
        PASSWORD = getpass.getpass("Nhập password: ").strip()

    chrome_opts = Options()
    chrome_opts.add_argument("--start-maximized")
    # không chạy headless để bạn có thể hoàn tất reCAPTCHA
    if chrome_user_data_dir:
        chrome_opts.add_argument(f"--user-data-dir={chrome_user_data_dir}")

    service = ChromeService(ChromeDriverManager().install())
    try:
        driver = webdriver.Chrome(service=service, options=chrome_opts)
    except WebDriverException as e:
        print("[!] Lỗi khởi tạo ChromeDriver:", e)
        return

    try:
        # Nếu có cookies sẵn, thử nạp và kiểm tra
        loaded = False
        if os.path.exists(COOKIES_PATH):
            try:
                loaded = load_cookies(driver, COOKIES_PATH)
            except Exception:
                loaded = False

        if loaded:
            # sau khi nạp cookies, mở lại panel để xem có đăng nhập được không
            driver.get("https://panel.hostmybot.net")
            time.sleep(3)
            # kiểm tra nếu URL chuyển tới dashboard hay vẫn ở login
            current = driver.current_url
            if current != PANEL_URL:
                print("[+] Có vẻ đã login tự động bằng cookie. URL:", current)
                print("Mở trình duyệt để tương tác. Script sẽ giữ trình duyệt mở.")
                while True:
                    time.sleep(1)
                return
            else:
                print("[*] Cookie nạp nhưng vẫn ở trang login (có thể cookie hết hạn). Tiếp tục flow login.")

        # Nếu tới đây, chưa login => thực hiện flow login thủ công + lưu cookie
        driver.get(PANEL_URL)
        time.sleep(1.2)

        username_selectors = [
            (By.CSS_SELECTOR, 'input[name="email"]'),
            (By.CSS_SELECTOR, 'input[name="username"]'),
            (By.CSS_SELECTOR, 'input[type="email"]'),
            (By.CSS_SELECTOR, 'input[placeholder*="Username"]'),
            (By.CSS_SELECTOR, 'input[placeholder*="Email"]'),
            (By.CSS_SELECTOR, 'input[autocomplete="username"]'),
        ]
        password_selectors = [
            (By.CSS_SELECTOR, 'input[name="password"]'),
            (By.CSS_SELECTOR, 'input[type="password"]'),
            (By.CSS_SELECTOR, 'input[autocomplete="current-password"]'),
            (By.CSS_SELECTOR, 'input[placeholder*="Password"]'),
        ]

        username_el = try_find(driver, username_selectors)
        password_el = try_find(driver, password_selectors)

        if username_el and password_el:
            try:
                username_el.clear()
                username_el.send_keys(USERNAME)
                password_el.clear()
                password_el.send_keys(PASSWORD)
                print("[+] Đã điền username & password.")
            except Exception as e:
                print("[!] Lỗi khi điền form:", e)
        else:
            print("[!] Không tìm thấy ô username/password tự động. Hãy điền tay trên trình duyệt.")

        print("\n==> BƯỚC TIẾP THEO:")
        print(" - Nếu trang hiển thị reCAPTCHA hoặc 2FA, hoàn tất TRÊN TRÌNH DUYỆT.")
        print(" - Khi sẵn sàng để submit, nhấn Enter tại terminal để script cố click Login (nếu có).")
        input("Nhấn Enter khi bạn đã hoàn tất captcha/2FA (hoặc sẵn sàng để submit): ")

        # Tìm nút Login
        login_selectors = [
            (By.CSS_SELECTOR, 'button[type="submit"]'),
            (By.XPATH, "//button[contains(., 'Login') or contains(., 'Sign In') or contains(., 'Đăng nhập')]"),
            (By.CSS_SELECTOR, 'button.btn-success'),
        ]
        login_button = try_find(driver, login_selectors)

        if login_button:
            try:
                login_button.click()
                print("[+] Đã click Login.")
            except ElementClickInterceptedException:
                try:
                    if password_el:
                        password_el.send_keys(Keys.ENTER)
                        print("[+] Gửi ENTER để submit form.")
                except Exception:
                    print("[!] Không thể click tự động, vui lòng click Login thủ công.")
        else:
            print("[!] Không tìm thấy nút Login tự động. Vui lòng click Login thủ công.")

        # đợi xử lý, sau đó thử lưu cookie nếu đăng nhập thành công
        time.sleep(5)
        current = driver.current_url
        print("URL hiện tại:", current)
        if current != PANEL_URL:
            print("[+] Có vẻ đã chuyển trang — lưu cookie...")
            save_cookies(driver, COOKIES_PATH)
        else:
            # có thể có thông báo lỗi => chờ user xử lý rồi lưu nếu họ muốn
            print("[*] Vẫn ở trang login. Nếu bạn hoàn tất login thủ công sau đó muốn lưu cookie, hãy nhấn 's' + Enter trong terminal để lưu cookie.")
            cmd = input("Gõ 's' để lưu cookie (hoặc Enter để thoát): ").strip().lower()
            if cmd == "s":
                save_cookies(driver, COOKIES_PATH)
                print("[+] Lưu cookie xong. Bạn có thể đăng xuất và chạy lại script để kiểm tra reuse.")

        print("Script giữ trình duyệt mở để bạn tương tác. Đóng terminal hoặc Ctrl+C để dừng.")
        while True:
            time.sleep(1)

    finally:
        try:
            driver.quit()
        except Exception:
            pass

if __name__ == "__main__":
    main()