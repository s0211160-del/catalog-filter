import requests
import xml.etree.ElementTree as ET

# ================= 設定區 =================
# 1. SHOPLINE 實際 XML 網址
XML_URL = "https://shopline-feeds.s3.amazonaws.com/facebook_featured_products/fmshoes.xml"

# 2. 標題/名稱排除關鍵字
TITLE_BLACKLIST = [
    "贈品", "測試", "紅包", "福利品", "牛仔帽", "四分襪", 
    "筒襪", "抗菌彈力棉襪", "開運發財襪", "可麗奶", "購物袋", 
    "殘膠清潔橡皮擦", "全方位擴鞋楦鞋器", "Ipanema", "Melissa"
]

# 3. 描述排除關鍵字
DESC_BLACKLIST = ["非賣品", "暫停銷售"]

# 4. 預設匯出檔名
OUTPUT_FILENAME = "catalog.xml"
# ==========================================

# 註冊與定義 XML 命名空間 (SHOPLINE 與 FB/Google Catalog 標準格式)
NAMESPACES = {
    'g': 'http://base.google.com/ns/1.0',
    'atom': 'http://www.w3.org/2005/Atom'
}

def get_node_text(item, tag_name):
    """
    同時支援尋找帶有 g: 前綴 (如 g:title) 或無前綴 (如 title) 的節點內容
    """
    # 1. 優先抓取帶有 g: 命名空間的標籤
    node = item.find(f'g:{tag_name}', NAMESPACES)
    if node is not None and node.text:
        return node.text.strip()
    
    # 2. 備用抓取無前綴的標準標籤
    node = item.find(tag_name)
    if node is not None and node.text:
        return node.text.strip()
        
    return ""

def run_filter():
    print("開始下載原始 XML...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    response = requests.get(XML_URL, headers=headers, timeout=30)
    response.raise_for_status()

    root = ET.fromstring(response.content)
    
    # 自動辨識商品容器節點
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
        # 提取標題、描述、庫存狀態 (全面支援 g:title / g:description / g:availability)
        title = get_node_text(item, 'title')
        desc = get_node_text(item, 'description')
        avail = get_node_text(item, 'availability').lower()

        # 1. 檢查標題關鍵字 (不分大小寫比對)
        if any(k.lower() in title.lower() for k in TITLE_BLACKLIST if k.strip()):
            container.remove(item)
            removed_count += 1
            continue

        # 2. 檢查描述關鍵字 (不分大小寫比對)
        if any(k.lower() in desc.lower() for k in DESC_BLACKLIST if k.strip()):
            container.remove(item)
            removed_count += 1
            continue

        # 3. 檢查是否缺貨
        if avail in ['out of stock', 'outofstock', '0', 'false']:
            container.remove(item)
            removed_count += 1
            continue

    # 註冊命名空間，確保匯出時保持原本的 g: 標籤完整結構
    for prefix, uri in NAMESPACES.items():
        ET.register_namespace(prefix, uri)

    # 寫入過濾後的 XML 檔案
    tree = ET.ElementTree(root)
    tree.write(OUTPUT_FILENAME, encoding='utf-8', xml_declaration=True)
    
    print(f"處理完成！原本 {total_initial} 筆，成功剔除 {removed_count} 筆，保留 {total_initial - removed_count} 筆。")
    print(f"檔案已儲存為 {OUTPUT_FILENAME}")

if __name__ == "__main__":
    run_filter()
