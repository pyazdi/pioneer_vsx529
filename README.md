# Async Pioneer VSX-529

NOT FINISHED YET!

My VSX-529 AV amp is not with the original Home Assistant Pioneer driver.
After some changes on the original driver it worked for a few hours, a day or two at max only. After that it freezes, and only a power off/on cycle makes it useable again.
This is because that driver creates a new telnet connection to the amp for every update, it queries the required info, and then closes the connection. The telnet software in the amp firmware probably has memory leak, that might be the reason for this freeze after a few thousands of telnet connections.

No firmware updates available for this amp anymore.

I found the work of [realthk](https://github.com/realthk) who did a amazing work for his Pioneer AV.
His AV has much more functions and didn't fit to my one.

So I took his async approach and merged it with the original HASS Pioneer driver.

## Install

1. Download and copy [media_player.py](https://github.com/realthk/asyncpioneer/blob/master/media_player.py) and [__init__.py](https://github.com/realthk/asyncpioneer/blob/master/__init__.py)into `config/custom_components/pioneer_vsx529` directory.

2. Add a reference to this inside your `configuration.yaml`:

  ```yaml
media_player:
  - platform: pioneer_vsx529
    host: 192.168.0.120
    port: 8102
    name: Pioneer VSX-529
    scan_interval: 1
    sources:
      'TV': '05'
      'Webradio': '38'
      'Alexa': '04'
  ```

## Options
**last_radio_station**:
If not set, "next track" button in radio tuner mode will simply send "next station" command to the amp, which is not convenient, if you only have a few stations stored in the amp's memory.
If this is set to eg. "B03", then sending a "next track" command when listening to "B03" will result in a "select A01 station" command. Likewise, a "previous track" on "A01" results in "select B03 station".

**radio_stations**:
You can name the stored stations here, because not every radio use RDS. Dictionary format.

**disabled_sources**:
A simple list to disable unwanted input sources, to make the source selector list shorter.

## Services
**pioneer_select_speaker**:

Select output speaker "A", "B" or "A+B"

  ```yaml
  - service: media_player.pioneer_select_speaker
    data:
      entity_id: media_player.pioneer_avr
      speaker: "A+B"
  ```

**pioneer_select_hdmi_out**:

Select HDMI output

  ```yaml
  - service: media_player.pioneer_select_hdmi_out
    data:
      entity_id: media_player.pioneer_avr
      hdmi_out: "1+2 ON"
  ```
where possible values for hdmi_out:

- "1+2 ON"
- "1 ON"
- "2 ON"
- "1/2 OFF"
 
  
**pioneer_select_radio_station**:

Select stored radio station by its name.

  ```yaml
  - service: media_player.pioneer_select_radio_station
    data:
      entity_id: media_player.pioneer_avr
      station: "My favorite radio"
```
**pioneer_dim_display**:

Dim the FL display in 4 levels

  ```yaml
  - service: media_player.pioneer_dim_display
    data:
      entity_id: media_player.pioneer_avr
      dim_display: 2
  ```
 where possible values for display brightness:

dim_display | Result
------------- | -------------
0 | Maximum brightness
1 | Bright display
2 | Dim display
3 | Display off
  
## State attributes
**current_radio_station**:
The currently selected radio station code, like "B07"

**current_speaker**:
The currently selected output speaker: "A", "B" or "A+B"
  ```yaml
{{ state_attr("media_player.pioneer_avr", "current_speaker") }}
```

**current_hdmi_out**:
The currently selected HDMI output: "1+2 ON", "1 ON", "2 ON", "1/2 OFF"
  ```yaml
{{ state_attr("media_player.pioneer_avr", "current_hdmi_out") }}
```
  
