import os
import requests
import xml.etree.ElementTree as ET
import pandas as pd

# ================= 設定區 =================
# 1. 請替換成您的實際 XML 網址
XML_URL = "https://shopline-feeds.s3.amazonaws.com/facebook_featured_products/fmshoes.xml"

# 2. 標題/名稱排除關鍵字
TITLE_BLACKLIST = ["贈品", "測試", "絕版", "福利品"]

# 3. 描述排除關鍵字
DESC_BLACKLIST = ["非賣品", "暫停銷售"]

# 4. 預設幣別與匯出檔名
CURRENCY = "TWD"
OUTPUT_FILENAME = "catalog.csv"
# ==========================================

def run_filter():
    print("開始下載 XML...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(XML_URL, headers=headers, timeout=30)
    response.raise_for_status()

    root = ET.fromstring(response.content)
    items = root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry') or root.findall('.//product')

    if not items:
        print("未找到商品資料！")
        return

    parsed_data = []
    for item in items:
        p_dict = {}
        for child in item:
            tag_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            p_dict[tag_name] = child.text.strip() if child.text else ""
        parsed_data.append(p_dict)

    df = pd.DataFrame(parsed_data)
    total_initial = len(df)
    print(f"成功解析 {total_initial} 筆商品數據。")

    # 1. 標題關鍵字排除
    if TITLE_BLACKLIST and 'title' in df.columns:
        pattern = "|".join([k.strip() for k in TITLE_BLACKLIST if k.strip()])
        df = df[~df['title'].astype(str).str.contains(pattern, case=False, na=False)]

    # 2. 描述關鍵字排除
    if DESC_BLACKLIST and 'description' in df.columns:
        pattern_desc = "|".join([k.strip() for k in DESC_BLACKLIST if k.strip()])
        df = df[~df['description'].astype(str).str.contains(pattern_desc, case=False, na=False)]

    # 3. 缺貨過濾
    if 'availability' in df.columns:
        df = df[~df['availability'].astype(str).str.lower().isin(['out of stock', 'outofstock', '0', 'false'])]

    # 4. 構建 FB/Google Catalog Schema
    output_df = pd.DataFrame()
    output_df['id'] = df['id'].astype(str) if 'id' in df.columns else df.index.astype(str)
    output_df['title'] = df['title'].astype(str) if 'title' in df.columns else ''
    output_df['description'] = df['description'].astype(str) if 'description' in df.columns else output_df['title']
    output_df['link'] = df['link'].astype(str) if 'link' in df.columns else ''
    output_df['image_link'] = df['image_link'].astype(str) if 'image_link' in df.columns else (df['g:image_link'].astype(str) if 'g:image_link' in df.columns else '')

    if 'price' in df.columns:
        prices = df['price'].astype(str)
        output_df['price'] = prices.apply(lambda p: p if any(c in p.upper() for c in ['TWD', 'USD', 'HKD', 'RMB']) else f"{p} {CURRENCY}")
    else:
        output_df['price'] = f"0 {CURRENCY}"

    output_df['availability'] = 'in stock'
    output_df['condition'] = 'new'

    # 匯出 CSV
    output_df.to_csv(OUTPUT_FILENAME, index=False, encoding='utf-8-sig')
    print(f"處理完成！保留 {len(output_df)} 筆，剔除 {total_initial - len(output_df)} 筆。檔案已儲存為 {OUTPUT_FILENAME}")

if __name__ == "__main__":
    run_filter()
