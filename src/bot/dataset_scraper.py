import os
import time
import uuid
import cv2
import numpy as np

def start_scraping(config: dict, adb_manager, duration_seconds=300, interval=3):
    """
    Emulator acikken belirtilen sure boyunca her X saniyede bir ekran goruntusu alir,
    tahtayi 15 hucreye boler ve 'dataset_raw' klasorune benzersiz isimlerle kaydeder.
    """
    # Hata ayıklama için fonksiyonun başladığını terminale kesin olarak basalım
    print("[Scraper Core] start_scraping fonksiyonu tetiklendi, veri toplama basliyor...")
    
    bbox = config["board_bounding_box"]
    cols = 5
    rows = 3
    
    # Ham resimlerin birikecegi gecici klasor
    output_dir = r"C:\Users\furkan\Desktop\ultimatebot\rush_royale_bot\dataset_raw"
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"[Scraper Core] Hedef Klasor: {output_dir}")
    print(f"[Scraper Core] {duration_seconds} saniye boyunca her {interval} saniyede bir hucreler kirpilecek.")
    
    start_time = time.time()
    saved_count = 0
    
    while time.time() - start_time < duration_seconds:
        try:
            # Doğrudan adb_manager nesnesi üzerinden ekran görüntüsünü alıyoruz
            frame = adb_manager.take_screenshot()
            
            if frame is None:
                print("[Scraper Core UYARI] ADB'den bos kare geldi, bir sonraki cevrim bekleniyor...")
                time.sleep(interval)
                continue
                
            board_crop = frame[bbox["y1"]:bbox["y2"], bbox["x1"]:bbox["x2"]]
            h, w, _ = board_crop.shape
            cell_w = w // cols
            cell_h = h // rows
            
            for r_idx in range(rows):
                for c_idx in range(cols):
                    x_start = c_idx * cell_w
                    y_start = r_idx * cell_h
                    cell_crop = board_crop[y_start:y_start+cell_h, x_start:x_start+cell_w]
                    
                    # Yeniden boyutlandirarak standart 64x64 formatina getiriyoruz
                    cell_resized = cv2.resize(cell_crop, (64, 64))
                    
                    # Dosya isimlerinin cakismamasi icin benzersiz bir ID (UUID) uretiyoruz
                    unique_id = uuid.uuid4().hex[:8]
                    file_name = f"raw_cell_{unique_id}.png"
                    file_path = os.path.join(output_dir, file_name)
                    
                    cv2.imwrite(file_path, cell_resized)
                    saved_count += 1
                    
            print(f"[Scraper Core] Toplam biriken hucre resmi sayisi: {saved_count}")
            
        except Exception as inner_error:
            print(f"[Scraper Core IC HATA] Dongu sirasinda hata olustu: {str(inner_error)}")
            
        time.sleep(interval)
        
    print(f"[Scraper Core] Islem tamamlandi! Toplam {saved_count} adet ham hucre resmi toplandi.")