import cv2
import json
import os
from src.adb.adb_manager import ADBManager

def check_grid_alignment():
    # 1. Config dosyasını yükle
    config_path = r"C:\Users\furkan\Desktop\ultimatebot\rush_royale_bot\config.json"
    with open(config_path, "r") as f:
        config = json.load(f)
        
    bbox = config["board_bounding_box"]
    cols, rows = 5, 3
    
    # 2. ADB bağlantısını kur ve anlık ekran görüntüsü al
    adb = ADBManager(config["adb_host"], config["adb_port"], config["package_name"])
    if not adb.connect():
        print("[HATA] ADB baglantisi kurulamadi. Portu kontrol edin!")
        return
        
    frame = adb.take_screenshot()
    if frame is None:
        print("[HATA] Ekran goruntusu alinamadi.")
        return
        
    # 3. Kırpma alanını görselleştir
    debug_img = frame.copy()
    
    # Ana tahta sınırlarını mavi dikdörtgenle çiz
    cv2.rectangle(debug_img, (bbox["x1"], bbox["y1"]), (bbox["x2"], bbox["y2"]), (255, 0, 0), 3)
    
    # Hücre kırpma mantığını simüle et
    board_w = bbox["x2"] - bbox["x1"]
    board_h = bbox["y2"] - bbox["y1"]
    cell_w = board_w // cols
    cell_h = board_h // rows
    
    for r in range(rows):
        for c in range(cols):
            x_start = bbox["x1"] + (c * cell_w)
            y_start = bbox["y1"] + (r * cell_h)
            
            # Her bir hücrenin sınırını yeşil ince çizgiyle çiz
            cv2.rectangle(debug_img, (x_start, y_start), (x_start + cell_w, y_start + cell_h), (0, 255, 0), 1)
            
    # Sonucu proje kök dizinine kaydet
    output_path = r"C:\Users\furkan\Desktop\ultimatebot\rush_royale_bot\grid_debug.png"
    cv2.imwrite(output_path, debug_img)
    print(f"[BAŞARILI] Hizalama kontrol resmi olusturuldu: {output_path}")
    print("[İPUCU] Resimdeki yesil karelerin kartlari tam ortalayip ortalamadigina bakip config'i güncelleyin.")

if __name__ == "__main__":
    check_grid_alignment()