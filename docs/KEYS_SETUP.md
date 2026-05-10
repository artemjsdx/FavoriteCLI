# FavoriteCLI Keys Setup

GitHub secret scanning blocks committing real keys.
Configure keys locally via the CLI or edit `config/api_keys.json` directly on your device.

## Quick setup via CLI
```bash
# OpenRouter (minimax/minimax-m2.5)
python -m favorite keys add openrouter --key sk-or-v1-YOUR_KEY --model minimax/minimax-m2.5

# FavoriteAPI (3 keys)
python -m favorite keys add favorite --key fa_sk_KEY1 --label key1 --default
python -m favorite keys add favorite --key fa_sk_KEY2 --label key2
python -m favorite keys add favorite --key fa_sk_KEY3 --label key3
```

## Manual setup
Edit `~/.config/favoritecli/api_keys.json` (or the config dir shown by `python -m favorite config path`).

## Key format
See `config/api_keys.json.template` in this repo for the expected JSON structure.