import re
import requests
import xml.etree.ElementTree as ET

# ================= 設定區 =================
# 1. SHOPLINE 實際 XML 網址
XML_URL = "https://shopline-feeds.s3.amazonaws.com/facebook_featured_products/fmshoes.xml"

# 2. 中文特定關鍵字黑名單
TITLE_BLACKLIST = [
    "贈品", "測試", "紅包", "福利品", "牛仔帽", "四分襪", 
    "筒襪", "抗菌彈力棉襪", "開運發財襪", "可麗奶", "購物袋", 
    "殘膠清潔橡皮擦", "全方位擴鞋楦鞋器", "Ipanema", "Melissa"
]

# 3. 描述排除關鍵字
DESC_BLACKLIST = ["非賣品", "暫停銷售"]

# 4. 自動排除開關（針對純數字/英文+數字）
REMOVE_NON_CHINESE_TITLES = True  # 設定為 True：自動刪除「完全不含中文」且「由英文/數字/符號組成」的標題

# 5. 預設匯出檔名
OUTPUT_FILENAME = "catalog.xml"
# ==========================================

NAMESPACES = {
    'g': 'http://base.google.com/ns/1.0',
    'atom': 'http://www.w3.org/2005/Atom'
}

def get_node_text(item, tag_name):
    node = item.find(f'g:{tag_name}', NAMESPACES)
    if node is not None and node.text:
        return node.text.strip()
    
    node = item.find(tag_name)
    if node is not None and node.text:
        return node.text.strip()
        
    return ""

def is_pure_alphanumeric_or_no_chinese(text):
    """
    檢查標題是否完全不包含中文字 (包含繁體/簡體字)
    若完全沒有中文字，且屬於數字、英文或符號組合，回傳 True
    """
    # 判斷是否包含中文字元
    has_chinese = bool(re.search(r'[\u4e00-\u9fff]', text))
    
    # 如果完全沒有中文，代表可能是純數字 (1023) 或英數組合 (A102 / NIKE123)
    if not has_chinese:
        return True
    return False

def run_filter():
    print("開始下載原始 SHOPLINE XML...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    response = requests.get(XML_URL, headers=headers, timeout=30)
    response.raise_for_status()

    root = ET.fromstring(response.content)
    
    channel = root.find('channel')
    if channel is not None:
        items = channel.findall('item')
        container = channel
    else:
        items = root.findall('.//item') or root.findall('.//entry')
        container = root

    total_initial = len(items)
    print(f"成功擷取到 {total_initial} 筆商品數據。")

    removed_count = 0

    for item in list(items):
        title = get_node_text(item, 'title')
        desc = get_node_text(item, 'description')
        avail = get_node_text(item, 'availability').lower()

        # 1. 檢查標題關鍵字黑名單
        if any(k.lower() in title.lower() for k in TITLE_BLACKLIST if k.strip()):
            container.remove(item)
            removed_count += 1
            continue

        # 2. 自動規則：排除無中文的「純數字 / 英數組合」標題
        if REMOVE_NON_CHINESE_TITLES and is_pure_alphanumeric_or_no_chinese(title):
            container.remove(item)
            removed_count += 1
            continue

        # 3. 檢查描述關鍵字
        if any(k.lower() in desc.lower() for k in DESC_BLACKLIST if k.strip()):
            container.remove(item)
            removed_count += 1
            continue

        # 4. 檢查庫存狀態 (剔除缺貨)
        if avail in ['out of stock', 'outofstock', '0', 'false']:
            container.remove(item)
            removed_count += 1
            continue

    for prefix, uri in NAMESPACES.items():
        ET.register_namespace(prefix, uri)

    tree = ET.ElementTree(root)
    tree.write(OUTPUT_FILENAME, encoding='utf-8', xml_declaration=True)
    
    print(f"處理完成！原始 {total_initial} 筆，自動剔除 {removed_count} 筆，保留 {total_initial - removed_count} 筆。")

if __name__ == "__main__":
    run_filter()
