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

# 註冊與定義 SHOPLINE/Google/Meta XML 的標準命名空間
NAMESPACES = {
    'g': 'http://base.google.com/ns/1.0',
    'atom': 'http://www.w3.org/2005/Atom'
}

def get_node_text(item, tag_name):
    """
    精準擷取節點文字，同時相容帶有 g: 命名空間與標準 XML 標籤
    """
    # 1. 優先尋找帶有 g: 命名空間的標籤 (如 g:title, g:description)
    node = item.find(f'g:{tag_name}', NAMESPACES)
    if node is not None and node.text:
        return node.text.strip()
    
    # 2. 備用尋找標準標籤 (如 title, description)
    node = item.find(tag_name)
    if node is not None and node.text:
        return node.text.strip()
        
    return ""

def run_filter():
    print("開始下載原始 SHOPLINE XML...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    response = requests.get(XML_URL, headers=headers, timeout=30)
    response.raise_for_status()

    # 解析 XML
    root = ET.fromstring(response.content)
    
    # 定位商品的 channel 容器
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
        # 提取商品屬性
        title = get_node_text(item, 'title')
        desc = get_node_text(item, 'description')
        avail = get_node_text(item, 'availability').lower()

        # 1. 檢查標題關鍵字 (不分大小寫)
        if any(k.lower() in title.lower() for k in TITLE_BLACKLIST if k.strip()):
            container.remove(item)
            removed_count += 1
            continue

        # 2. 檢查描述關鍵字 (不分大小寫)
        if any(k.lower() in desc.lower() for k in DESC_BLACKLIST if k.strip()):
            container.remove(item)
            removed_count += 1
            continue

        # 3. 檢查庫存狀態 (剔除缺貨商品)
        if avail in ['out of stock', 'outofstock', '0', 'false']:
            container.remove(item)
            removed_count += 1
            continue

    # 註冊命名空間，確保匯出時保留完整的 <g:xxx> 標籤結構
    for prefix, uri in NAMESPACES.items():
        ET.register_namespace(prefix, uri)

    # 寫入檔案
    tree = ET.ElementTree(root)
    tree.write(OUTPUT_FILENAME, encoding='utf-8', xml_declaration=True)
    
    print(f"處理完成！原始 {total_initial} 筆，成功剔除 {removed_count} 筆，保留 {total_initial - removed_count} 筆。")
    print(f"過濾後的檔案已儲存為 {OUTPUT_FILENAME}")

if __name__ == "__main__":
    run_filter()
