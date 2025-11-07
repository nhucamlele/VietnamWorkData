import time
import json
import random
import os
import subprocess
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

# ==== CONFIG ====
START_URL = "https://www.vietnamworks.com/it-kw"
BASE_URL = "https://www.vietnamworks.com"
JSON_PATH = "vietnamworks_it_filtered.json"

CHROME_OPTIONS_LIST = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-gpu",
    "--incognito",
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.179 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:116.0) Gecko/20100101 Firefox/116.0",
]

# ==== LƯU / CẬP NHẬT JSON ====
def save_or_update_json(new_data, file_path=JSON_PATH):
    if os.path.exists(file_path):
        try:
            with open(file_path, encoding="utf-8") as f:
                old_data = json.load(f)
                if not isinstance(old_data, list):
                    old_data = []
        except Exception as e:
            print("⚠️ Không đọc được file cũ, sẽ tạo mới:", e)
            old_data = []
    else:
        old_data = []

    old_urls = {item.get("Url") for item in old_data if isinstance(item, dict) and item.get("Url")}
    fresh_data = [job for job in new_data if job.get("Url") not in old_urls]

    if not fresh_data:
        print("✅ Không có job mới để thêm.")
        return

    print(f"🆕 Phát hiện {len(fresh_data)} job mới → thêm lên đầu file cũ...")
    updated = fresh_data + old_data

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(updated, f, ensure_ascii=False, indent=2)

    print(f"💾 Đã cập nhật {file_path}: tổng {len(updated)} job.")

# ==== KHỞI TẠO DRIVER AN TOÀN ====
def init_uc_driver(headless=False, retries=3):
    """Khởi tạo undetected_chromedriver an toàn, retry nếu crash."""
    for attempt in range(1, retries + 1):
        try:
            options = uc.ChromeOptions()
            for opt in CHROME_OPTIONS_LIST:
                options.add_argument(opt)
            options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")
            if headless:
                options.add_argument("--headless")  # không dùng --headless=new
            driver = uc.Chrome(options=options)
            driver.maximize_window()
            wait = WebDriverWait(driver, 20)
            print(f"✅ Chrome driver khởi tạo thành công (attempt {attempt})")
            return driver, wait
        except Exception as e:
            print(f"⚠️ Lỗi khởi tạo Chrome driver (attempt {attempt}): {e}")
            time.sleep(3)
    raise RuntimeError("❌ Không thể khởi tạo Chrome driver sau nhiều lần thử")

def ensure_driver_alive(driver):
    try:
        driver.current_url
        return driver
    except:
        print("⚠️ Driver bị đóng, khởi tạo lại...")
        driver, _ = init_uc_driver(headless=False)
        return driver

# ==== LẤY DANH SÁCH JOB URL ====
def get_job_links(driver, wait, start_url, limit=9999):
    driver = ensure_driver_alive(driver)
    driver.get(start_url)
    time.sleep(7)
    print(f"🌐 Đang load danh sách job từ: {start_url}")

    seen_count = 0
    stagnant_rounds = 0
    total_rounds = 0

    while True:
        total_rounds += 1
        driver.execute_script("window.scrollBy(0, 1000);")
        time.sleep(random.uniform(1.5, 3.5))
        job_blocks = driver.find_elements(By.CSS_SELECTOR, "div.sc-cvalOF.fsOPJQ")
        current_count = len(job_blocks)
        print(f"🌀 Lần cuộn {total_rounds}: hiện có {current_count} job hiển thị")

        if current_count == seen_count:
            stagnant_rounds += 1
        else:
            stagnant_rounds = 0
            seen_count = current_count

        if stagnant_rounds >= 5 or total_rounds >= 80:
            print("✅ Không thấy job mới, dừng cuộn.")
            break

    print(f"🏁 Hoàn tất load danh sách ({seen_count} job).")

    job_urls = []
    for i, block in enumerate(job_blocks[:limit], start=1):
        try:
            job_a = block.find_element(By.CSS_SELECTOR, "div.sc-eTTeRg.jkvCZV a")
            job_url = job_a.get_attribute("href")
            if job_url and not job_url.startswith("http"):
                job_url = BASE_URL + job_url
            if job_url:
                job_urls.append(job_url)
                print(f"{i}. 🔗 {job_url}")
        except:
            print(f"{i}. ⚠️ Không tìm thấy link job.")
    print(f"✅ Tổng cộng {len(job_urls)} link hợp lệ được thu thập.")
    return job_urls

# ==== LẤY THÔNG TIN JOB ====
def get_job_info(driver, job_url):
    driver = ensure_driver_alive(driver)
    driver.get(job_url)
    for _ in range(5):
        driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(random.uniform(1, 2))
    for _ in range(5):
        driver.execute_script("window.scrollBy(0, -800);")
        time.sleep(random.uniform(0.5, 1.5))
    time.sleep(random.uniform(2, 4))

    job_name = salary = None
    location = posted_time = skills = job_domain = None
    company_url = None

    try:
        view_more_btn = driver.find_element(By.CSS_SELECTOR, "button.sc-bd699a4b-0.eOtpMH")
        driver.execute_script("arguments[0].click();", view_more_btn)
        time.sleep(2)
    except: pass

    try: job_name = driver.find_element(By.CSS_SELECTOR, "h1").text.strip()
    except: pass
    try: salary = driver.find_element(By.CSS_SELECTOR, "span.sc-ab270149-0.cVbwLK").text.strip()
    except: pass
    try:
        company_a = driver.find_element(By.CSS_SELECTOR, "div.sc-37577279-3.drWnZq a.sc-ab270149-0.egZKeY")
        company_url = company_a.get_attribute("href")
    except: pass
    try:
        location_header = driver.find_element(By.XPATH, "//h2[contains(text(), 'Job Locations')]")
        parent = location_header.find_element(By.XPATH, "./..")
        loc_elems = parent.find_elements(By.CSS_SELECTOR, "p.sc-ab270149-0")
        locations = [loc.text.strip() for loc in loc_elems if loc.text.strip()]
        if locations: location = ". ".join(locations)
    except: pass
    try:
        info_blocks = driver.find_elements(By.CSS_SELECTOR, "div.sc-7bf5461f-1.jseBPO div")
        for block in info_blocks:
            try:
                label = block.find_element(By.CSS_SELECTOR, "label.sc-ab270149-0.dfyRSX").text.strip().upper()
                value = None
                try: value = block.find_element(By.CSS_SELECTOR, "p.sc-ab270149-0").text.strip()
                except: pass
                if not value: continue
                if "POSTED DATE" in label: posted_time = value
                elif "SKILL" in label: skills = value
                elif "JOB FUNCTION" in label: job_domain = value
            except: continue
    except Exception as e: print("⚠️ Không tìm thấy block info:", e)

    return {
        "Job_name": job_name,
        "Location": location,
        "Salary": salary,
        "Posted_time": posted_time,
        "Skills": skills,
        "Working_days": "Monday-Friday",
        "Working_type": "At office",
        "Job_domain": job_domain,
        "Company_url": company_url
    }

# ==== LẤY THÔNG TIN COMPANY ====
def get_company_info(driver, company_url):
    driver = ensure_driver_alive(driver)
    driver.get(company_url)
    time.sleep(random.uniform(2, 4))
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)

    company_name = company_size = company_address = company_industry = None
    try:
        name_el = driver.find_element(By.CSS_SELECTOR, "div.sc-ca95509a-6.cXJgQF h1.sc-ca95509a-8.gcvyPj")
        company_name = name_el.text.strip()
    except: pass
    try:
        lis = driver.find_elements(By.CSS_SELECTOR, "ul.sc-7f4c261d-5.kfIkVN li.sc-7f4c261d-6.ejuuLs")
        for li in lis:
            try:
                label = li.find_element(By.CSS_SELECTOR, "p.type").text.strip().lower()
                value = None
                if "size" in label or "industry" in label:
                    value = li.find_element(By.CSS_SELECTOR, "p.text").text.strip()
                elif "address" in label:
                    value = li.find_element(By.CSS_SELECTOR, "span.sc-fTyFcS.fWdnij").text.strip()
                if "size" in label: company_size = value
                elif "address" in label: company_address = value
                elif "industry" in label: company_industry = value
            except: continue
    except: pass

    if not company_size:
        return None  # loại job

    return {
        "Company": company_name,
        "Company size": company_size,
        "Address": company_address,
        "Company industry": company_industry
    }

# ==== MAIN LOOP ====
def main():
    driver, wait = init_uc_driver(headless=False)
    results = []
    old_urls = set()
    if os.path.exists(JSON_PATH):
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            try:
                old_data = json.load(f)
                old_urls = {item.get("Url") for item in old_data if isinstance(item, dict) and item.get("Url")}
                print(f"📂 Đã tải {len(old_urls)} job cũ.")
            except Exception: print("⚠️ File cũ lỗi định dạng, bỏ qua.")
    else:
        print("🆕 Không có file cũ, sẽ cào toàn bộ.")
    try:
        for page in range(1, 3):
            time.sleep(random.uniform(5, 9))
            page_url = f"https://www.vietnamworks.com/jobs?q=it&page={page}&sorting=relevant"
            print(f"\n==============================")
            print(f"🌐 ĐANG CÀO TRANG {page}: {page_url}")
            print(f"==============================")
            job_urls = get_job_links(driver, wait, page_url, limit=9999)
            for idx, job_url in enumerate(job_urls, start=1):
                if job_url in old_urls:
                    print("⏭️ Job đã tồn tại, bỏ qua:", job_url)
                    continue

                print(f"\n{idx}. 🔍 Cào job detail: {job_url}")
                job_info = get_job_info(driver, job_url)
                if not job_info.get("Company_url"):
                    print("⚠️ Bỏ qua job này vì không có Company URL.")
                    continue

                company_info = get_company_info(driver, job_info["Company_url"])
                if not company_info:
                    print("⚠️ Bỏ qua job vì Company size trống.")
                    continue

                results.append({
                    "Url": job_url,
                    "Job name": job_info.get("Job_name"),
                    "Company Name": company_info.get("Company"),
                    "Address": job_info.get("Location"),
                    "Company type": job_info.get("Working_type"),
                    "Time": job_info.get("Posted_time"),
                    "Skills": job_info.get("Skills"),
                    "Salary": job_info.get("Salary"),
                    "Company industry": company_info.get("Company industry"),
                    "Company size": company_info.get("Company size"),
                    "Working days": job_info.get("Working_days")
                })

        print(f"\n🎯 Tổng số job mới cào được: {len(results)}")
        save_or_update_json(results, JSON_PATH)
    finally:
        driver.quit()

    # ==== GitHub auto push ====
    print("\n🚀 Đang cập nhật GitHub...")
    try:
        subprocess.run(["git", "-C", os.getcwd(), "add", JSON_PATH])
        subprocess.run(["git", "-C", os.getcwd(), "add", __file__])
        subprocess.run(["git", "-C", os.getcwd(), "commit", "-m", "auto update VietnamWorks data and scraper"])
        subprocess.run(["git", "-C", os.getcwd(), "push", "origin", "main"])
        print("✅ Hoàn tất cập nhật GitHub.")
    except Exception as e:
        print("⚠️ Lỗi khi cập nhật GitHub:", e)

if __name__ == "__main__":
    main()
