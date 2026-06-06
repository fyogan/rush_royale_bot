import os
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image

class RushRoyaleNet(nn.Module):
    """
    Multi-Head CNN: Kart tipi ve Rank bilgisini bağımsız öğrenir.
    """
    def __init__(self):
        super(RushRoyaleNet, self).__init__()
        
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2, 2), # 32x32
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(2, 2), # 16x16
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.MaxPool2d(2, 2)  # 8x8
        )
        
        self.fc_common = nn.Sequential(
            nn.Linear(128 * 8 * 8, 128),
            nn.ReLU(),
            nn.Dropout(0.3)
        )
        
        self.type_head = nn.Linear(128, 6) # Kart Tipleri
        self.rank_head = nn.Linear(128, 6) # Rank Seviyeleri (0-5)

    def forward(self, x):
        x = self.features(x)
        x = x.view(x.size(0), -1)
        x = self.fc_common(x)
        return self.type_head(x), self.rank_head(x)

class RushRoyaleDataset(Dataset):
    """
    Dosya isimlerini güvenle ayrıştıran, hatalı isimleri es geçen Dataset.
    """
    def __init__(self, image_dir, transform=None):
        self.image_dir = image_dir
        self.transform = transform
        self.samples = []
        
        valid_files = [f for f in os.listdir(image_dir) if f.endswith(('.png', '.jpg', '.jpeg'))]
        print(f"[DATASET] {len(valid_files)} dosya analiz ediliyor...")

        for img_name in valid_files:
            try:
                # Format: cell_class1_rank3_12345.png
                parts = img_name.split('_')
                # class'tan sonraki sayıyı al (0-5 arası)
                card_type = int(parts[1].replace('class', ''))
                # rank'ten sonraki sayıyı al (0-5 arası)
                card_rank = int(parts[2].replace('rank', ''))
                
                # Sınır denetimi (Modelin kafaları 0-5 arası tanımlı)
                if 0 <= card_type <= 5 and 0 <= card_rank <= 5:
                    self.samples.append((os.path.join(image_dir, img_name), card_type, card_rank))
            except (IndexError, ValueError):
                continue
        print(f"[DATASET] Eğitim için {len(self.samples)} geçerli örnek yüklendi.")

    def __len__(self): return len(self.samples)

    def __getitem__(self, idx):
        path, t, r = self.samples[idx]
        img = Image.open(path).convert('RGB')
        return self.transform(img) if self.transform else img, t, r

def get_data_transforms():
    # 64x64 çözünürlük korunuyor
    t = transforms.Compose([
        transforms.Resize((64, 64)),
        transforms.RandomRotation(degrees=180),
        transforms.ColorJitter(brightness=0.2, contrast=0.2),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    return t, t

def train_model(data_dir, save_path="rush_royale_net.pth"):
    transform, _ = get_data_transforms()
    dataset = RushRoyaleDataset(data_dir, transform)
    if len(dataset) == 0: return
    
    loader = DataLoader(dataset, batch_size=32, shuffle=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = RushRoyaleNet().to(device)
    
    opt = torch.optim.Adam(model.parameters(), lr=0.001)
    
    print(f"Eğitim başlıyor: {device}")
    model.train()
    
    for epoch in range(15):
        running_loss = 0.0
        for imgs, types, ranks in loader:
            imgs, types, ranks = imgs.to(device), types.to(device), ranks.to(device)
            opt.zero_grad()
            t_out, r_out = model(imgs)
            # Rank hatalarını daha ağır cezalandır (1.5x)
            loss = nn.CrossEntropyLoss()(t_out, types) + (nn.CrossEntropyLoss()(r_out, ranks) * 1.5)
            loss.backward()
            opt.step()
            running_loss += loss.item()
        print(f"Epoch {epoch+1} tamamlandı. Loss: {running_loss/len(loader):.4f}")
        
    torch.save(model.state_dict(), save_path)
    print("Model kaydedildi.")

if __name__ == "__main__":
    DATA_DIR = r"C:\Users\furkan\Desktop\ultimatebot\rush_royale_bot\dataset_cells"
    MODEL_SAVE_PATH = r"C:\Users\furkan\Desktop\ultimatebot\rush_royale_bot\src\bot\rush_royale_net.pth"
    train_model(DATA_DIR, MODEL_SAVE_PATH)