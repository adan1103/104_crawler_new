import requests
import json
import time
import pandas as pd
import re

AREA_CODES = {
    "台北市": "6001001000",
    "新北市": "6001002000",
    "桃園市": "6001003000",
    "台中市": "6001004000",
    "高雄市": "6001005000",
    "台南市": "6001006000",
    "新竹縣": "6001007000",
    "新竹市": "6001008000",
    "苗栗縣": "6001009000",
    "彰化縣": "6001011000",
    "雲林縣": "6001012000",
    "嘉義市": "6001010000",
    "嘉義縣": "6001011000",
    "屏東縣": "6001013000",
    "宜蘭縣": "6001015000",
    "花蓮縣": "6001014000",
    "台東縣": "6001016000",
    "基隆市": "6001017000",
    "南投縣": "6001018000",
    "澎湖縣": "6001019000",
    "金門縣": "6001020000",
    "連江縣": "6001021000",
}

# ====== 讀取 config.txt ======
def read_config(filename):
    """讀取 config.txt 並自動轉換中文地區名稱"""
    params = {}
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            value = value.strip()
            # 自動轉換地區名稱
            if key == "area":
                areas = [a.strip() for a in value.split(",")]
                codes = []
                for a in areas:
                    if a in AREA_CODES:
                        codes.append(AREA_CODES[a])
                    else:
                        print(f"⚠️ 無法辨識地區名稱：{a}")
                value = ",".join(codes)
            params[key.strip()] = value
    return params


# ====== 抓取職缺清單 ======
def fetch_job_list(params):
    url = "https://www.104.com.tw/jobs/search/list"
    headers = {
        "Referer": "https://www.104.com.tw/jobs/search/",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                      "Version/17.0 Safari/605.1.15"
    }

    res = requests.get(url, headers=headers, params=params)
    res.raise_for_status()
    data = res.json()
    return data["data"]["list"]


# ====== 抓取職缺詳細資料 ======
def fetch_job_detail(job_id):
    import requests

    job_id = job_id.split("?")[0].split("/")[-1]
    url = f"https://www.104.com.tw/job/ajax/content/{job_id}"

    headers = {
        "Referer": f"https://www.104.com.tw/job/{job_id}",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                      "Version/17.0 Safari/605.1.15"
    }

    res = requests.get(url, headers=headers)
    res.raise_for_status()
    data = res.json()

    if not data.get("data"):
        raise ValueError("此職缺資料不完整或已下架")

    info = data["data"]

    # 各層結構
    header = info.get("header", {})
    detail = info.get("jobDetail", {})
    condition = info.get("condition", {})
    cust = info.get("custInfo", {})
    welfare = info.get("welfare", {})

    # ===== 公司名稱與職缺名稱 =====
    company_name = (
        info.get("custName")
        or cust.get("custName")
        or header.get("custName")
        or "（未知公司）"
    )

    job_name = (
        detail.get("jobName")
        or header.get("jobName")
        or info.get("jobName")
        or "（未命名職缺）"
    )

    # ===== 語言能力 =====
    lang_list = []
    for lang in condition.get("language", []):
        lang_item = lang.get("language", "")
        ability = lang.get("ability", "")
        if lang_item:
            lang_list.append(f"{lang_item}:{ability}" if ability else lang_item)
    language = ", ".join(lang_list) if lang_list else "未指定"

    # ===== 擅長工具 =====
    specialty = ""
    if isinstance(condition.get("specialty"), list):
        specialty_list = [sp.get("desc", "") for sp in condition.get("specialty", []) if sp.get("desc")]
        specialty = ", ".join(specialty_list)
    elif isinstance(condition.get("specialty"), str):
        specialty = condition.get("specialty")
    elif detail.get("specialty"):
        specialty = detail.get("specialty")

    if not specialty:
        specialty = "未指定"

    # ===== 工作技能 =====
    skills = ""
    if isinstance(condition.get("skill"), list):
        skill_list = [sk.get("desc", "") for sk in condition.get("skill", []) if sk.get("desc")]
        skills = ", ".join(skill_list)
    elif isinstance(condition.get("skill"), str):
        skills = condition.get("skill")
    elif detail.get("skill"):
        skills = detail.get("skill")

    if not skills:
        skills = "未指定"

    # ===== 其他條件 =====
    other_condition = (
        condition.get("other")  # 有些公司放在 condition.other
        or detail.get("otherCondition")  # 有些放 jobDetail.otherCondition
        or info.get("requirement", {}).get("other")  # 或 requirement.other
        or ""
    )
    other_condition = str(other_condition).replace("\r\n", " ").strip()

    # ===== 輸出結果 =====
    job_data = {
        "公司名稱": company_name,
        "職缺名稱": job_name,
        "地點": (detail.get("addressRegion", "") or "") + (detail.get("addressDetail", "") or ""),
        "工作經歷": condition.get("workExp", ""),
        "學歷": condition.get("edu", ""),
        "語言能力": language,
        "擅長工具": specialty,
        "工作技能": skills,
        "薪資": detail.get("salary", ""),
        "福利": welfare.get("welfare", ""),
        "職缺需求人數": detail.get("needEmp", ""),
        "工作內容": (detail.get("jobDescription", "") or "").replace("\r\n", " ").strip(),
        "其他條件": other_condition,
        "職缺更新日期": header.get("appearDate", ""),
        "職缺連結": f"https://www.104.com.tw/job/{job_id}",
    }

    return job_data

# ====== 主程式 ======
if __name__ == "__main__":
    params = read_config("config.txt")
    job_list = fetch_job_list(params)

    all_jobs = []
    for job in job_list:
        job_id = job["link"]["job"]
        try:
            job_data = fetch_job_detail(job_id)
            all_jobs.append(job_data)
            print(f"✅ 已抓取：{job_data['職缺名稱']} - {job_data['公司名稱']}")
            time.sleep(1)  # 延遲防止被封鎖
        except Exception as e:
            print(f"⚠️ 跳過職缺：{job_id}，原因：{e}")

    # ====== 儲存結果 ======
    if all_jobs:
        df = pd.DataFrame(all_jobs)
        df.to_excel("104_jobs.xlsx", index=False)
        print("\n🎉 已完成，結果已存到 104_jobs.xlsx")
    else:
        print("❌ 沒有成功抓取到任何職缺。")
