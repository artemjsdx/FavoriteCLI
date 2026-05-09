import json, sys
cfg_path = '/storage/emulated/0/Цхранилище/Project/FavoriteCLI/config/api_keys.json'
cfg = json.load(open(cfg_path))
cfg['favorite_api_base_url'] = 'https://variance-dreams-major-stock.trycloudflare.com'
json.dump(cfg, open(cfg_path, 'w'), indent=2, ensure_ascii=False)
print('CFG updated:', cfg['favorite_api_base_url'])
