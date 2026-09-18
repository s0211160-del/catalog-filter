import requests
import xml.etree.ElementTree as ET

# ================= 設定區 =================
# 1. 請替換成您的實際 XML 網址
XML_URL = "https://example.com/catalog.xml"

# 2. 標題/名稱排除關鍵字
TITLE_BLACKLIST = ["贈品", "測試", "絕版", "福利品"]

# 3. 描述排除關鍵字
DESC_BLACKLIST = ["非賣品", "暫停銷售"]

# 4. 預設匯出檔名
OUTPUT_FILENAME = "catalog.xml"
# ==========================================

def run_filter():
    print("開始下載原始 XML...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(XML_URL, headers=headers, timeout=30)
    response.raise_for_status()

    root = ET.fromstring(response.content)
    
    # 自動辨識常見的 XML/RSS 結構節點
    channel = root.find('channel')
    if channel is not None:
        items = channel.findall('item')
        container = channel
    else:
        items = root.findall('.//item') or root.findall('.//entry') or root.findall('.//product')
        container = root

    total_initial = len(items)
    print(f"成功擷取到 {total_initial} 筆商品數據。")

    removed_count = 0

    for item in list(items):
        # 取得商品標題與描述內容
        title_node = item.find('title')
        desc_node = item.find('description')
        avail_node = item.find('availability') or item.find('{http://base.google.com/ns/1.0}availability')

        title = title_node.text if (title_node is not None and title_node.text) else ""
        desc = desc_node.text if (desc_node is not None and desc_node.text) else ""
        avail = avail_node.text.lower() if (avail_node is not None and avail_node.text) else ""

        # 1. 檢查標題關鍵字
        if any(k in title for k in TITLE_BLACKLIST if k):
            container.remove(item)
            removed_count += 1
            continue

        # 2. 檢查描述關鍵字
        if any(k in desc for k in DESC_BLACKLIST if k):
            container.remove(item)
            removed_count += 1
            continue

        # 3. 檢查是否缺貨
        if avail in ['out of stock', 'outofstock', '0', 'false']:
            container.remove(item)
            removed_count += 1
            continue

    # 將過濾後的 XML 結構寫入檔案
    tree = ET.ElementTree(root)
    tree.write(OUTPUT_FILENAME, encoding='utf-8', xml_declaration=True)
    
    print(f"處理完成！保留 {total_initial - removed_count} 筆，剔除 {removed_count} 筆。")
    print(f"檔案已儲存為 {OUTPUT_FILENAME}")

if __name__ == "__main__":
    run_filter()
