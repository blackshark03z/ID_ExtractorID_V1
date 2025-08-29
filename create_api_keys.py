import os
import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def load_gmail_list():
    """Đọc danh sách Gmail từ file gmail_list.txt"""
    gmail_list = []
    try:
        with open("gmail_list.txt", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "|" in line:
                        email, password = line.split("|", 1)
                        gmail_list.append({
                            "email": email.strip(),
                            "password": password.strip()
                        })
    except FileNotFoundError:
        print("❌ Không tìm thấy file gmail_list.txt")
        return []
    
    if not gmail_list:
        print("❌ Không có Gmail nào trong file gmail_list.txt")
        return []
    
    print(f"✅ Đã tải {len(gmail_list)} Gmail accounts")
    return gmail_list

def load_proxy_list():
    """Đọc danh sách proxy từ file proxy_list.txt"""
    proxy_list = []
    try:
        with open("proxy_list.txt", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if ":" in line:
                        parts = line.split(":")
                        if len(parts) == 2:
                            # ip:port
                            proxy_list.append({
                                "ip": parts[0],
                                "port": parts[1],
                                "username": None,
                                "password": None
                            })
                        elif len(parts) == 4:
                            # ip:port:username:password
                            proxy_list.append({
                                "ip": parts[0],
                                "port": parts[1],
                                "username": parts[2],
                                "password": parts[3]
                            })
    except FileNotFoundError:
        print("⚠️  Không tìm thấy file proxy_list.txt - Sẽ không sử dụng proxy")
        return []
    
    if not proxy_list:
        print("⚠️  Không có proxy nào trong file proxy_list.txt - Sẽ không sử dụng proxy")
        return []
    
    print(f"✅ Đã tải {len(proxy_list)} proxy")
    return proxy_list

def get_random_proxy(proxy_list):
    """Lấy proxy ngẫu nhiên từ danh sách"""
    if not proxy_list:
        return None
    return random.choice(proxy_list)

def setup_chrome_driver(proxy=None):
    """Thiết lập Chrome driver với proxy"""
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Thêm proxy nếu có
    if proxy:
        proxy_string = f"{proxy['ip']}:{proxy['port']}"
        if proxy['username'] and proxy['password']:
            # Proxy có authentication
            chrome_options.add_argument(f'--proxy-server={proxy_string}')
            # Tạo extension để xác thực proxy
            proxy_auth_extension = create_proxy_auth_extension(
                proxy['ip'], proxy['port'], proxy['username'], proxy['password']
            )
            chrome_options.add_extension(proxy_auth_extension)
        else:
            # Proxy không có authentication
            chrome_options.add_argument(f'--proxy-server={proxy_string}')
        
        print(f"  🌐 Sử dụng proxy: {proxy['ip']}:{proxy['port']}")
    
    # Thêm User-Agent ngẫu nhiên
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]
    chrome_options.add_argument(f'--user-agent={random.choice(user_agents)}')
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def create_proxy_auth_extension(proxy_host, proxy_port, proxy_user, proxy_pass):
    """Tạo extension để xác thực proxy"""
    import tempfile
    import zipfile
    
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        },
        "minimum_chrome_version":"22.0.0"
    }
    """
    
    background_js = """
    var config = {
        mode: "fixed_servers",
        rules: {
            singleProxy: {
                scheme: "http",
                host: "%s",
                port: parseInt(%s)
            },
            bypassList: ["localhost"]
        }
    };

    chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

    function callbackFn(details) {
        return {
            authCredentials: {
                username: "%s",
                password: "%s"
            }
        };
    }

    chrome.webRequest.onAuthRequired.addListener(
        callbackFn,
        {urls: ["<all_urls>"]},
        ['blocking']
    );
    """ % (proxy_host, proxy_port, proxy_user, proxy_pass)
    
    # Tạo file extension tạm thời
    temp_dir = tempfile.mkdtemp()
    manifest_file = os.path.join(temp_dir, "manifest.json")
    background_file = os.path.join(temp_dir, "background.js")
    
    with open(manifest_file, 'w') as f:
        f.write(manifest_json)
    with open(background_file, 'w') as f:
        f.write(background_js)
    
    # Tạo file zip
    extension_file = os.path.join(temp_dir, "proxy_auth_extension.zip")
    with zipfile.ZipFile(extension_file, 'w') as zp:
        zp.write(manifest_file, "manifest.json")
        zp.write(background_file, "background.js")
    
    return extension_file

def create_api_key_manual(gmail_info):
    """Hướng dẫn tạo API key thủ công"""
    print(f"\n📧 Đang tạo API key cho: {gmail_info['email']}")
    print("=" * 50)
    
    steps = [
        "1. Mở trình duyệt và truy cập: https://console.cloud.google.com/",
        "2. Đăng nhập bằng Gmail: " + gmail_info['email'],
        "3. Tạo project mới hoặc chọn project có sẵn",
        "4. Bật Gemini API: https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com",
        "5. Tạo API key: https://console.cloud.google.com/apis/credentials",
        "6. Copy API key và nhập vào đây"
    ]
    
    for step in steps:
        print(step)
        time.sleep(1)
    
    api_key = input(f"\n🔑 Nhập API key cho {gmail_info['email']}: ").strip()
    return api_key

def update_api_keys_file(api_keys):
    """Cập nhật file api_keys.txt"""
    try:
        with open("api_keys.txt", "w", encoding="utf-8") as f:
            f.write("# Danh sách API Keys cho Gemini\n")
            f.write("# Mỗi dòng một key, bỏ trống dòng để bỏ qua\n")
            f.write("# Key hiện tại:\n")
            for key in api_keys:
                if key:
                    f.write(key + "\n")
        
        print(f"✅ Đã cập nhật {len(api_keys)} API keys vào file api_keys.txt")
    except Exception as e:
        print(f"❌ Lỗi cập nhật file: {e}")

def main():
    print("🚀 Bắt đầu tạo API keys từ danh sách Gmail...")
    
    # Đọc danh sách Gmail
    gmail_list = load_gmail_list()
    if not gmail_list:
        return
    
    # Đọc danh sách proxy
    proxy_list = load_proxy_list()
    
    print(f"\n📋 Danh sách Gmail:")
    for i, gmail in enumerate(gmail_list, 1):
        print(f"  {i}. {gmail['email']}")
    
    if proxy_list:
        print(f"\n🌐 Danh sách Proxy:")
        for i, proxy in enumerate(proxy_list, 1):
            auth_info = f" (Auth: {proxy['username']})" if proxy['username'] else ""
            print(f"  {i}. {proxy['ip']}:{proxy['port']}{auth_info}")
    
    # Hỏi người dùng có muốn tạo API key tự động không
    choice = input(f"\n❓ Bạn có muốn tạo API key tự động cho {len(gmail_list)} Gmail? (y/n): ").strip().lower()
    
    if choice == 'y':
        print("\n⚠️  Lưu ý: Tạo API key tự động có thể:")
        print("- Mất nhiều thời gian")
        print("- Cần xác thực 2 yếu tố")
        print("- Có thể bị Google chặn")
        
        confirm = input("Bạn có chắc chắn muốn tiếp tục? (y/n): ").strip().lower()
        if confirm != 'y':
            print("❌ Đã hủy tạo API key tự động")
            return
        
        # Tạo API key tự động
        api_keys = []
        for i, gmail in enumerate(gmail_list, 1):
            print(f"\n[{i}/{len(gmail_list)}] Đang xử lý: {gmail['email']}")
            
            # Lấy proxy ngẫu nhiên cho mỗi Gmail
            proxy = get_random_proxy(proxy_list) if proxy_list else None
            
            try:
                api_key = create_api_key_auto(gmail, proxy)
                if api_key:
                    api_keys.append(api_key)
                    print(f"✅ Đã tạo API key cho {gmail['email']}")
                else:
                    print(f"❌ Không thể tạo API key cho {gmail['email']}")
            except Exception as e:
                print(f"❌ Lỗi tạo API key cho {gmail['email']}: {e}")
            
            # Delay ngẫu nhiên để tránh bị phát hiện
            delay = random.uniform(3, 8)
            print(f"⏳ Chờ {delay:.1f} giây...")
            time.sleep(delay)
        
        # Cập nhật file
        if api_keys:
            update_api_keys_file(api_keys)
    
    else:
        # Hướng dẫn tạo thủ công
        print("\n📝 Hướng dẫn tạo API key thủ công:")
        api_keys = []
        
        for gmail in gmail_list:
            api_key = create_api_key_manual(gmail)
            if api_key:
                api_keys.append(api_key)
        
        # Cập nhật file
        if api_keys:
            update_api_keys_file(api_keys)

def create_api_key_auto(gmail_info, proxy=None):
    """Tạo API key tự động (cần cài đặt selenium)"""
    driver = None
    try:
        driver = setup_chrome_driver(proxy)
        
        # Đăng nhập Google
        print(f"  🔐 Đang đăng nhập {gmail_info['email']}...")
        driver.get("https://accounts.google.com/signin")
        
        # Nhập email
        email_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "identifier"))
        )
        email_input.send_keys(gmail_info['email'])
        driver.find_element(By.ID, "identifierNext").click()
        
        # Nhập mật khẩu
        password_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "password"))
        )
        password_input.send_keys(gmail_info['password'])
        driver.find_element(By.ID, "passwordNext").click()
        
        # Chờ đăng nhập thành công
        time.sleep(5)
        
        # Truy cập Google Cloud Console
        print("  🌐 Đang truy cập Google Cloud Console...")
        driver.get("https://console.cloud.google.com/")
        time.sleep(3)
        
        # Tạo project mới (nếu cần)
        try:
            create_project_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Create Project')]"))
            )
            create_project_btn.click()
            
            project_name = f"Gemini-Project-{int(time.time())}"
            project_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "projectName"))
            )
            project_input.send_keys(project_name)
            
            driver.find_element(By.XPATH, "//button[contains(text(), 'Create')]").click()
            time.sleep(5)
        except:
            print("  ℹ️  Sử dụng project hiện có")
        
        # Bật Gemini API
        print("  🔧 Đang bật Gemini API...")
        driver.get("https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com")
        time.sleep(3)
        
        try:
            enable_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Enable')]"))
            )
            enable_btn.click()
            time.sleep(3)
        except:
            print("  ℹ️  Gemini API đã được bật")
        
        # Tạo API key
        print("  🔑 Đang tạo API key...")
        driver.get("https://console.cloud.google.com/apis/credentials")
        time.sleep(3)
        
        create_credentials_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Create Credentials')]"))
        )
        create_credentials_btn.click()
        
        api_key_option = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'API key')]"))
        )
        api_key_option.click()
        time.sleep(3)
        
        # Lấy API key
        api_key_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@readonly]"))
        )
        api_key = api_key_element.get_attribute("value")
        
        # Đóng popup
        driver.find_element(By.XPATH, "//button[contains(text(), 'Close')]").click()
        
        return api_key
        
    except Exception as e:
        print(f"  ❌ Lỗi: {e}")
        return None
    
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main() 