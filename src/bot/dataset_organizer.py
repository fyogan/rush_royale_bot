import os
import shutil
import uuid

def build_and_rename_dataset(config: dict, vision_manager):
    """
    sorter_zone altındaki hiyerarşik klasörleri tarar.
    Kart tipini ana klasör adından, rank değerini ise alt klasör adından (1,2,3)
    okuyarak 'dataset_cells' klasörüne kusursuz formatta kopyalar.
    """
    base_sorter_dir = r"C:\Users\furkan\Desktop\ultimatebot\rush_royale_bot\sorter_zone"
    target_dataset_dir = r"C:\Users\furkan\Desktop\ultimatebot\rush_royale_bot\dataset_cells"
    
    os.makedirs(target_dataset_dir, exist_ok=True)
    
    # Ana klasörler ve class_id eşleşmeleri
    folder_mapping = {
        "0_empty": 0,
        "1_dryad": 1,
        "2_harlequin": 2,
        "3_mime": 3,
        "4_trapper": 4,
        "5_bruiser": 5
    }
    
    print("[Organizer Core] Klasor hiyerarsisi tabanli etiketleme basladi...")
    total_processed = 0
    
    for folder_name, class_id in folder_mapping.items():
        main_folder_path = os.path.join(base_sorter_dir, folder_name)
        
        if not os.path.exists(main_folder_path):
            print(f"[Organizer Core UYARI] Klasor bulunamadi, atlaniyor: {main_folder_path}")
            continue
            
        # 0_empty klasörü için özel durum (Alt klasörü yoktur, rank doğrudan 0'dır)
        if class_id == 0:
            files = [f for f in os.listdir(main_folder_path) if f.endswith(('.png', '.jpg', '.jpeg'))]
            for file_name in files:
                src_file_path = os.path.join(main_folder_path, file_name)
                unique_suffix = uuid.uuid4().hex[:6]
                new_file_name = f"cell_class0_rank0_{unique_suffix}.png"
                dest_file_path = os.path.join(target_dataset_dir, new_file_name)
                shutil.copy(src_file_path, dest_file_path)
                total_processed += 1
            continue
            
        # Diğer kartlar için alt klasörleri (1, 2, 3, 4, 5) tara
        for rank_folder in ["1", "2", "3", "4", "5"]:
            sub_folder_path = os.path.join(main_folder_path, rank_folder)
            
            if not os.path.exists(sub_folder_path):
                continue # Eğer o rank klasörü henüz açılmadıysa veya boşsa atla
                
            files = [f for f in os.listdir(sub_folder_path) if f.endswith(('.png', '.jpg', '.jpeg'))]
            
            if len(files) > 0:
                print(f"[Organizer Core] '{folder_name}/{rank_folder}' icinde {len(files)} adet resim tasnif ediliyor...")
                
            for file_name in files:
                src_file_path = os.path.join(sub_folder_path, file_name)
                
                # Benzersiz dosya adı üretimi: Klasörden gelen kesin class ve kesin rank basılıyor!
                unique_suffix = uuid.uuid4().hex[:6]
                new_file_name = f"cell_class{class_id}_rank{rank_folder}_{unique_suffix}.png"
                dest_file_path = os.path.join(target_dataset_dir, new_file_name)
                
                shutil.copy(src_file_path, dest_file_path)
                total_processed += 1
                
    print(f"[Organizer Core SUCCESS] Islem tamamlandi! Toplam {total_processed} adet veri, net tiple ve net rankla 'dataset_cells' klasorune aktarildi.")

if __name__ == "__main__":
    pass