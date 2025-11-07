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

def save_or_update_json(new_data, file_path=JSON_PATH):
    if os.path.exists(file_path):
        try:
            with open(file_path, encoding="utf-8") as f:
                old_data = json.load(f)
                if not isinstance(old_data, list):
                    old_data = []
        except:
            old_data = []
    else:
        old_data = []

    old_urls = {item.get("Url") for item in old_data if isinstance(item, dict) and item.get("Url")}
    fresh_data = [job for job in new_data if job.get("Url") not in old_urls]

    if not fresh_data:
        print("✅ Không có job mới.")
        return

    updated = fresh_data + old_data
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(updated, f, ensure_ascii=False, indent=2)

    print(f"💾 Đã cập nhật {file_path}: tổng {len(updated)} job.")

def init_uc_driver(headless=False, retries=3):
    for attempt in range(1, retries + 1):
        try:
            options = uc.ChromeOptions()
            for opt in CHROME_OPTIONS_LIST:
                options.add_argument(opt)
            options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")
            if headless:
                options.add_argument("--headless")
            driver = uc.Chrome(options=options)
            driver.maximize_window()
            wait = WebDriverWait(driver, 20)
            print("✅ Chrome driver khởi tạo")
            return driver, wait
        except:
            time.sleep(3)
    raise RuntimeError("❌ Không thể khởi tạo driver")

def ensure_driver_alive(driver):
    try:
        driver.current_url
        return driver
    except:
        driver, _ = init_uc_driver(headless=False)
        return driver

# ==== LIST JOB URL & ADDRESS ====
def get_job_links(driver, wait, start_url, limit=9999):
    driver = ensure_driver_alive(driver)
    driver.get(start_url)
    time.sleep(7)

    seen_count = 0
    stagnant_rounds = 0

    while True:
        driver.execute_script("window.scrollBy(0, 1000);")
        time.sleep(random.uniform(1.5, 3.5))
        job_blocks = driver.find_elements(By.CSS_SELECTOR, "div.sc-cvalOF.fsOPJQ")
        current = len(job_blocks)

        if current == seen_count:
            stagnant_rounds += 1
        else:
            stagnant_rounds = 0
            seen_count = current

        if stagnant_rounds >= 5:
            break

    job_list = []
    for block in job_blocks[:limit]:
        try:
            job_a = block.find_element(By.CSS_SELECTOR, "div.sc-eTTeRg.jkvCZV a")
            job_url = job_a.get_attribute("href")
            if job_url and not job_url.startswith("http"):
                job_url = BASE_URL + job_url

            try:
                location = block.find_element(By.CSS_SELECTOR, "span.sc-fTyFcS.fWdnij").text.strip()
            except:
                location = None

            if job_url:
                job_list.append((job_url, location))
        except:
            continue

    return job_list

# ==== JOB DETAIL ====
def get_job_info(driver, job_url):
    driver.get(job_url)
    time.sleep(random.uniform(2, 4))

    job_name = salary = posted_time = skills = job_domain = None
    company_url = None

    try:
        job_name = driver.find_element(By.CSS_SELECTOR, "h1").text.strip()
    except: pass

    try:
        salary = driver.find_element(By.CSS_SELECTOR, "span.sc-ab270149-0.cVbwLK").text.strip()
    except: pass

    try:
        company_a = driver.find_element(By.CSS_SELECTOR, "div.sc-37577279-3.drWnZq a.sc-ab270149-0.egZKeY")
        company_url = company_a.get_attribute("href")
    except: pass

    # ✅ Lấy POSTED DATE / SKILL / JOB FUNCTION
    try:
        info_blocks = driver.find_elements(By.CSS_SELECTOR, "div.sc-7bf5461f-1.jseBPO div")
        for block in info_blocks:
            try:
                label = block.find_element(By.CSS_SELECTOR, "label").text.strip().upper()
                value = block.find_element(By.CSS_SELECTOR, "p, span").text.strip()
                if not value:
                    continue

                if "POSTED DATE" in label:
                    posted_time = value
                elif "SKILL" in label:
                    skills = value
                elif "JOB FUNCTION" in label:
                    job_domain = value
            except:
                continue
    except:
        pass

    return {
        "Job_name": job_name,
        "Salary": salary,
        "Posted_time": posted_time,
        "Skills": skills,
        "Job_domain": job_domain,
        "Company_url": company_url
    }

# ==== COMPANY INFO ====
def get_company_info(driver, company_url):
    driver.get(company_url)
    time.sleep(3)

    company_name = company_size = company_industry = None

    try:
        company_name = driver.find_element(By.CSS_SELECTOR, "div.sc-ca95509a-6.cXJgQF h1.sc-ca95509a-8.gcvyPj").text.strip()
    except: pass

    lis = driver.find_elements(By.CSS_SELECTOR, "ul.sc-7f4c261d-5.kfIkVN li.sc-7f4c261d-6.ejuuLs")
    for li in lis:
        try:
            label = li.find_element(By.CSS_SELECTOR, "p.type").text.strip().lower()
            value = li.find_element(By.CSS_SELECTOR, "p.text").text.strip()
            if "size" in label: company_size = value
            if "industry" in label: company_industry = value
        except:
            continue

    if not company_size:
        return None

    return {
        "Company": company_name,
        "Company size": company_size,
        "Company industry": company_industry
    }

# ==== MAIN ====
def main():
    driver, wait = init_uc_driver(headless=False)
    results = []
    old_urls = set()

    if os.path.exists(JSON_PATH):
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            old_data = json.load(f)
            old_urls = {item.get("Url") for item in old_data if isinstance(item, dict)}

    for page in range(10, 20):
        page_url = f"https://www.vietnamworks.com/jobs?q=it&page={page}&sorting=relevant"
        print(f"\n==============================")
        print(f"🌐 ĐANG CÀO TRANG {page}")
        print(f"==============================")
        job_list = get_job_links(driver, wait, page_url)

        for job_url, location in job_list:
            if job_url in old_urls:
                continue

            job_info = get_job_info(driver, job_url)
            if not job_info.get("Company_url"):
                continue

            company_info = get_company_info(driver, job_info["Company_url"])
            if not company_info:
                continue

            results.append({
                "Url": job_url,
                "Job name": job_info["Job_name"],
                "Company Name": company_info["Company"],
                "Address": location,
                "Company type": "At office",
                "Time": job_info["Posted_time"],
                "Skills": job_info["Skills"],
                "Job domain": job_info["Job_domain"],
                "Salary": job_info["Salary"],
                "Company industry": company_info["Company industry"],
                "Company size": company_info["Company size"],
                "Working days": "Monday-Friday"
            })

    save_or_update_json(results, JSON_PATH)
    driver.quit()

# ==== AUTO PUSH ====
def auto_git_push(commit_msg="update data"):
    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("✅ Auto push thành công")
    except:
        print("⚠️ Không có thay đổi hoặc push lỗi")

if __name__ == "__main__":
    main()
    auto_git_push("update: scrape data with Address & Posted/Skills fix")
