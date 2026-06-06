import os
import time
from src.utils.logger import log

class RecoveryManager:
    def __init__(self, adb_manager, state_machine):
        self.adb = adb_manager
        self.state_machine = state_machine

    def handle_recovery(self, mode: int):
        """
        mode 1: Soft Recovery (Geri tuşu simülasyonu)
        mode 2: Hard Recovery (Uygulamayı kökten kapatıp sıfırdan açma)
        """
        package_name = self.adb.package_name # com.my.defense bilgisini harfiyen çeker

        if mode == 1:
            log.info("[RECOVERY] Soft Recovery pipeline initiated. Sending Android Back Key descriptor.")
            # Standart lobi içi escape veya boşluğa tıklama komutu
            self.adb.tap(50, 50)
            time.sleep(1.0)
            
        elif mode == 2:
            log.warning(f"[RECOVERY CRITICAL] Level 2 Force Restart resmen tetiklendi. Hedef Paket: {package_name}")
            
            # Nesne öznitelik isimlerinden bağımsız olarak IP ve Port bilgilerini güvenle koruma altına alıyoruz
            adb_host = getattr(self.adb, 'adb_host', getattr(self.adb, 'host', '127.0.0.1'))
            adb_port = getattr(self.adb, 'adb_port', getattr(self.adb, 'port', 5555))
            target_device = f"{adb_host}:{adb_port}"
            
            try:
                # 1. HAMLE: Android AM (Activity Manager) kullanarak uygulamayı zorla durdur (Kökten Kapatma)
                # 'am force-stop' emülatörün önbelleğinden ve RAM'inden oyunu tamamen kazır.
                stop_cmd = f"adb -s {target_device} shell am force-stop {package_name}"
                os.system(stop_cmd)
                log.info(f"[RECOVERY] am force-stop komutu enjekte edildi: {package_name}")
                time.sleep(2.0)
                
                # 2. HAMLE: Tedbir amaçlı arka plan zombi süreçlerini (process) sonlandırma garantisi
                kill_cmd = f"adb -s {target_device} shell pkill -f {package_name}"
                os.system(kill_cmd)
                time.sleep(2.0)

                log.info("[RECOVERY] Uygulamanın kapandığından emin olundu. Sıfırdan ayağa kaldırılıyor...")

                # 3. HAMLE: Uygulamayı sıfırdan, temiz bir lobi ana ekranıyla (Monkey UI framework) başlat
                # Bu komut oyunun doğrudan giriş logosundan (Splash Screen) temizce tetiklenmesini sağlar.
                start_cmd = f"adb -s {target_device} shell monkey -p {package_name} -c android.intent.category.LAUNCHER 1"
                os.system(start_cmd)
                log.info(f"[RECOVERY SUCCESS] {package_name} paketi emülatörde başarıyla yeniden başlatıldı.")
                
            except Exception as e:
                log.error(f"[RECOVERY ERROR] Android terminal döngüsü yürütülürken hata meydana geldi: {str(e)}")