import time
from src.utils.logger import log

class DecisionEngine:
    def __init__(self, config: dict, board_manager, adb_manager):
        self.config = config
        self.board = board_manager
        self.adb = adb_manager
        
        # Kahraman yeteneği ve kart geliştirmeleri için zaman sayaçları
        self.last_hero_upgrade = 0
        self.last_card_upgrade = 0
        
        # Oyun başı agresif kart çağırma mekanizması (Summon Rush)
        self.summon_rush_count = 0
        self.summon_rush_limit = 20
        self.last_summon_time = 0

    def reset_battle_state(self):
        """Yeni bir maça girildiğinde sayaçları sıfırlar."""
        log.info("[DECISION] Yeni mac tespit edildi, oyun basi Summon Rush sayaci sifirlaniyor.")
        self.summon_rush_count = 0
        self.last_summon_time = 0

    def execute_battle_logic(self, mana: int, frame) -> bool:
        """
        Savaş alanındaki parametreleri değerlendirerek hamle kararı üretir.
        ULTRA FAST - SUMMON RUSH IVMELENDIRMESI EKLEDNI.
        """
        current_time = time.time()

        # =========================================================================
        # 1. AŞAMA: OYUN BAŞI ULTRA AGRESİF SUMMON RUSH FAZI (Zaman Kilitsiz)
        # =========================================================================
        if self.summon_rush_count < self.summon_rush_limit:
            log.info(f"[DECISION - SUMMON RUSH] Işık hızı modu aktif! Kalan basım: {self.summon_rush_limit - self.summon_rush_count}")
            
            # 🚀 DARBOĞAZI KALDIRDIK: 
            # Saniyede veya 0.2 saniyede bir basmak yerine, tek frame yakalamasında 
            # arka arkaya 4-5 kez tıklama emrini gecikmesiz (No-Delay) gönderiyoruz.
            burst_size = min(5, self.summon_rush_limit - self.summon_rush_count)
            
            for _ in range(burst_size):
                self.summon_rush_count += 1
                # ADB enjeksiyonunu ardı ardına yapıyoruz
                self.adb.tap(779, 766)
                
            # Küçük bir işletim sistemi nefes alma payı (Milisaniyelik)
            time.sleep(0.05) 
            return True

        # =========================================================================
        # 2. AŞAMA: YAPAY ZEKA VE STRATEJİK DÖNGÜ FAZI (Tahta Dolduktan Sonra)
        # =========================================================================
        
        # Mana okuması başarısız veya sıfır geldiyse akışı korumak için güvenli bir taban değer atıyoruz
        if mana is None or mana <= 0:
            mana = 100

        # Kartların anlık konumlarını ve oylama hafızasını güncelle
        self.board.update_board(frame)
        
        # Boş slot ve tahtadaki toplam kart sayılarını alıyoruz
        empty_slots = 0
        tracked_cards = 0
        
        for cell, data in self.board.memory.items():
            if data["card"] == "empty":
                empty_slots += 1
            else:
                tracked_cards += 1

        log.info(f"[DECISION - BOARD STATUS] Toplam Hucre Metrikleri: Bos Slot={empty_slots}/15 | Tespit Edilen Kart={tracked_cards}")

        # Koşul A: Tahtada boş yer varsa ve yeterli mana varsa kart çağır (0.2sn Gecikme Senkronlu)
        if empty_slots > 0 and mana >= 150:
            log.info("[DECISION - SUMMON] Tahtada bos yer tespit edildi. Kart cagirma koordinatına basiliyor: (779, 766)")
            self.adb.tap(779, 766)
            return True

        # Koşul B: Belirli periyotlarla Mana ile Bruiser kart seviyesini yükselt (Power Up)
        if mana >= 500 and (current_time - self.last_card_upgrade > 45):
            log.info("[DECISION - UPGRADE] Yuksek mana birikti. Bruiser kart seviyesi yukseltiliyor.")
            self.adb.tap(250, 830) # Arayüzdeki kart yükseltme buton koordinatınız
            self.last_card_upgrade = current_time
            return True

        # Koşul C: Tahta tamamen dolduysa akıllı ve hızlı birleştirme (Merge) algoritması
        if empty_slots == 0:
            log.info("[DECISION - MERGE] Tahta tamamen dolu! Yapay zeka kombinasyon arıyor...")
            
            # Hafızada bir önceki hamlenin takılıp kalmadığını doğrulamak için kısa bir check
            for cell_a, data_a in self.board.memory.items():
                if data_a["card"] == "empty": continue
                    
                for cell_b, data_b in self.board.memory.items():
                    if cell_a == cell_b or data_b["card"] == "empty": continue
                        
                    # Kart isimleri ve rankları uyuşuyorsa
                    if data_a["card"] == data_b["card"] and data_a["rank"] == data_b["rank"]:
                        loc_a = self.board.get_cell_coordinates(cell_a)
                        loc_b = self.board.get_cell_coordinates(cell_b)
                        
                        log.info(f"[DECISION - MERGE EXECUTE] Hızlı Sürükleme: {data_a['card']} R{data_a['rank']} [{cell_a} -> {cell_b}]")
                        
                        # 🚀 HIZ OPTİMİZASYONU: Swipe süresini 300ms'den 150ms'ye düşürdük (Işık hızı enjeksiyon)
                        self.adb.swipe(loc_a[0], loc_a[1], loc_b[0], loc_b[1], 150)
                        
                        # 💡 HATA TOLERANSI: Oyundaki animasyonun tamamlanması ve modelin 
                        # hayalet kart görmemesi için en ideal "ışık hızı" bekleme süresi: 0.15 saniye
                        time.sleep(0.15)
                        return True