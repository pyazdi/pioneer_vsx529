# Async Pioneer VSX-529

My VSX-529 AV amp is not working with the original Home Assistant Pioneer driver.
This repository is based on https://github.com/SpaceMaster85/pioneer_vsx529 that works on my AV very well but I need some more features like selecting Internet Radio sender and Media Server.

## Install

1. Download and copy [media_player.py](https://github.com/pyazdi/pioneer_vsx529/blob/master/media_player.py) and [init.py](https://github.com/pyazdi/pioneer_vsx529/blob/master/__init__.py) and [manifest.json](https://github.com/pyazdi/pioneer_vsx529/blob/master/manifest.json) into `config/custom_components/pioneer_vsx529` directory.

2. Add a reference to this inside your `configuration.yaml`:

  ```yaml
media_player:
  - platform: pioneer_vsx529
    host: 192.168.0.XXX
    port: 8102
    name: Pioneer VSX-529
    sources:
      'Netradio': '38'
      'DVD': '04'
      'TV': '05'
      'Sat/Cbl': '06'
      'HDMI/MHL': '48'
      'Media Server': '44'
      'Favorites': '45'
      'Game': '49'
  ```

I run it on Home Assistant 2021.11.5

