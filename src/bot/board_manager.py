import os
import cv2
import numpy as np
from collections import deque
from typing import Dict, Any, List, Tuple
import torch
from torchvision import transforms
from PIL import Image

from src.vision.vision_manager import VisionManager
from src.utils.logger import log
from src.bot.model_pipeline import RushRoyaleNet

class BoardManager:
    def __init__(self, config: dict, vision_manager: VisionManager):
        self.config = config
        self.vision = vision_manager
        self.bbox = self.config["board_bounding_box"]
        self.cols = 5
        self.rows = 3
        self.cell_names = [
            ["A1", "B1", "C1", "D1", "E1"],
            ["A2", "B2", "C2", "D2", "E2"],
            ["A3", "B3", "C3", "D3", "E3"]
        ]
        
        self.class_mapping = {0: "empty", 1: "dryad", 2: "harlequin", 3: "mime", 4: "trapper", 5: "bruiser"}
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = RushRoyaleNet()
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(current_dir, "rush_royale_net.pth")
        
        try:
            self.model.load_state_dict(torch.load(model_path, map_location=self.device, weights_only=True))
            log.info(f"[INFO] - [Neural Network] Multi-Head model {self.device.type.upper()} modunda yuklendi.")
        except FileNotFoundError:
            log.warning("[Neural Network] Model dosyasi bulunamadi!")
            
        self.model.to(self.device).eval()
        
        # 🚀 64x64 Standartlaştırma
        self.inference_transform = transforms.Compose([
            transforms.Resize((64, 64)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

        self.memory: Dict[str, Dict[str, Any]] = {}
        self.history: Dict[str, deque] = {}
        self.initialize_memory()

    def initialize_memory(self):
        for row in self.cell_names:
            for cell in row:
                self.memory[cell] = {
                    "card": "empty",
                    "rank": 0,
                    "confidence_type": 0.0,
                    "confidence_tier": 0.0
                }
                self.history[cell] = deque([("empty", 0)] * 5, maxlen=5)

    def _predict_cell_cnn(self, cell_img: np.ndarray) -> Tuple[int, int, float, float]:
        """Multi-Head Çıkarım: Tip ve Rank için bağımsız tahmin."""
        if cell_img is None: return 0, 0, 0.0, 0.0
            
        rgb_img = cv2.cvtColor(cell_img, cv2.COLOR_BGR2RGB)
        input_tensor = self.inference_transform(Image.fromarray(rgb_img)).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            type_logits, rank_logits = self.model(input_tensor)
            
            t_probs = torch.softmax(type_logits, dim=1)
            r_probs = torch.softmax(rank_logits, dim=1)
            
            t_id = torch.argmax(t_probs, dim=1).item()
            r_id = torch.argmax(r_probs, dim=1).item()
            
            return t_id, r_id, float(t_probs[0][t_id].item()), float(r_probs[0][r_id].item())

    def update_board(self, frame: np.ndarray):
        if frame is None: return
        board_crop = frame[self.bbox["y1"]:self.bbox["y2"], self.bbox["x1"]:self.bbox["x2"]]
        h, w, _ = board_crop.shape
        cell_w, cell_h = w // self.cols, h // self.rows

        for r_idx in range(self.rows):
            for c_idx in range(self.cols):
                cell_name = self.cell_names[r_idx][c_idx]
                cell_crop = board_crop[r_idx*cell_h:(r_idx+1)*cell_h, c_idx*cell_w:(c_idx+1)*cell_w]

                t_id, r_id, c_t, c_r = self._predict_cell_cnn(cell_crop)
                card_name = self.class_mapping.get(t_id, "empty")
                
                self.history[cell_name].append((card_name, r_id))
                self.resolve_voting_decision(cell_name, c_t, c_r)

    def resolve_voting_decision(self, cell_name: str, c_t: float, c_r: float):
        history_list = list(self.history[cell_name])
        
        # Oylama mantığı (en çok tekrar edenleri al)
        cards = [x[0] for x in history_list]
        ranks = [x[1] for x in history_list]
        
        best_card = max(set(cards), key=cards.count)
        best_rank = max(set(ranks), key=ranks.count)
        
        self.memory[cell_name] = {
            "card": best_card,
            "rank": best_rank,
            "confidence_type": c_t,
            "confidence_tier": c_r
        }

    def get_cell_coordinates(self, cell_name: str) -> Tuple[int, int]:
        # ... (Eski koordinat fonksiyonun aynısı kalabilir) ...
        for r in range(self.rows):
            if cell_name in self.cell_names[r]:
                c = self.cell_names[r].index(cell_name)
                h = self.bbox["y2"] - self.bbox["y1"]
                w = self.bbox["x2"] - self.bbox["x1"]
                return self.bbox["x1"] + (c * (w // self.cols)) + ((w // self.cols) // 2), \
                       self.bbox["y1"] + (r * (h // self.rows)) + ((h // self.rows) // 2)
        return 0, 0