import json
import os
from src.gui.gui_manager import BotGUIManager
from src.utils.logger import log

def load_configuration(config_path: str = "config.json") -> dict:
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Critical configuration source missing structural path target: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    log.info("System initializing runtime process.")
    try:
        config = load_configuration("config.json")
        app = BotGUIManager(config)
        app.mainloop()
    except Exception as e:
        log.critical(f"Fatal crash tracked during initialization sequence phase: {str(e)}")

if __name__ == "__main__":
    main()