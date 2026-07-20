import json
import os

config_path = os.path.expanduser("~/.config/opencode/opencode.json")
with open(config_path, "r") as f:
    config = json.load(f)

if "glmllb" in config.get("provider", {}):
    if "models" not in config["provider"]["glmllb"]:
        config["provider"]["glmllb"]["models"] = {}
    config["provider"]["glmllb"]["models"]["kimi-k2.7"] = {
        "id": "kimi-k2.7",
        "name": "Kimi 2.7 (via Cloudflare)"
    }
    
with open(config_path, "w") as f:
    json.dump(config, f, indent=2)

print("Updated config successfully.")
