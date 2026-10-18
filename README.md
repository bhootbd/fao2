# fao2
Archive and template catalog of the `ig_meme_templatesofficial` Telegram channel, built the same
way as `bhootbd/fao`: `scripts/tg_scrape.py` saves the channel into `archive/<channel>/`, then each
file is described in `catalog.json` and renamed to a descriptive name.

## Template catalog

`archive/ig_meme_templatesofficial/catalog.json` has one entry per file (key, file, Telegram link,
caption, title, who, what_happens, key_line for dialogue clips, audio, emotion, use_when, tags, note),
and every file in `media/` has a descriptive name. `transcripts.json` keeps transcripts for dialogue
clips only. To copy everything to Google Drive, open `github_to_drive.ipynb` in Colab and Run all.
