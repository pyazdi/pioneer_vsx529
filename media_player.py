"""Support for Pioneer Network Receivers."""
import logging
import asyncio
import time

import voluptuous as vol

from homeassistant.components.media_player import MediaPlayerEntity, MediaPlayerEntityFeature, PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    CONF_TIMEOUT,
    STATE_OFF,
    STATE_ON,
    EVENT_HOMEASSISTANT_STOP
)
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

CONF_SOURCES = "sources"

DEFAULT_NAME = "Pioneer AVR"
DEFAULT_PORT = 8102  # telnet default. Some Pioneer AVRs use 8102
DEFAULT_TIMEOUT = None
DEFAULT_SOURCES = {}

DATA_PIONEER = 'pioneer'

MAX_VOLUME = 160
MAX_SOURCE_NUMBERS = 60

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): cv.socket_timeout,
        vol.Optional(CONF_SOURCES, default=DEFAULT_SOURCES): {cv.string: cv.string},
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Pioneer platform."""
    pioneer = PioneerDevice(
        hass,
        config[CONF_NAME],
        config[CONF_HOST],
        config[CONF_PORT],
        config[CONF_TIMEOUT],
        config[CONF_SOURCES],
    )

    hass.loop.create_task(pioneer.readdata())

    if DATA_PIONEER not in hass.data:
        hass.data[DATA_PIONEER] = []
    hass.data[DATA_PIONEER].append(pioneer)

    _LOGGER.debug("adding pioneer entity")
    async_add_entities([pioneer], update_before_add=False)

    # Build the source name dictionaries if necessary
    if not config[CONF_SOURCES]:
        for i in range(MAX_SOURCE_NUMBERS):
            try:
                await asyncio.wait_for(pioneer.query_source(i), timeout=5)
            except asyncio.TimeoutError:
                print("Source query timeout occurred")


class PioneerDevice(MediaPlayerEntity):
    """Representation of a Pioneer device."""
    _attr_supported_features = (
        MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_STEP
    )

    def __init__(self, hass, name, host, port, timeout, sources):
        """Initialize the Pioneer device."""
        self._name = name
        self._host = host
        self._port = port
        self._timeout = timeout
        self._volume = 0
        self._muted = False
        self._selected_source = ""
        self._source_name_to_number = sources
        self._source_number_to_name = dict((v, k) for k, v in sources.items())
        
        self._power = False

        self._async_added = False
        self._stop_listen = False
        self.hasConnection = False
        self.reader = None
        self.writer = None
        self.processed = asyncio.Condition()

        hass.bus.async_listen(EVENT_HOMEASSISTANT_STOP, self.stop_pioneer)

    def stop_pioneer(self, event):
        _LOGGER.info("Shutting down Pioneer")
        self._stop_listen = True


    async def async_added_to_hass(self):
        _LOGGER.debug("Async async_added_to_hass")
        self._async_added = True
    
    async def query_source(self, num):
        self.telnet_command(f"?RGB{str(num).zfill(2)}")
        async with self.processed:
            await self.processed.wait()

    async def readdata(self):
        _LOGGER.debug("Readdata")

        while not self._stop_listen:
            if not self.hasConnection:
                try:
                    self.reader, self.writer = \
                        await asyncio.open_connection(self._host, self._port)
                    self.hasConnection = True
                    _LOGGER.info("Connected to %s:%d", self._host, self._port)
                    self.telnet_command("?P")  # Power state?
                    self.telnet_command("?V")  # Volume?
                    self.telnet_command("?M")  # Muted?
                    self.telnet_command("?F")  # Input source?

                except:
                    _LOGGER.error("No connection to %s:%d, retry in 30s", \
                        self._host, self.port)
                    await asyncio.sleep(30)
                    continue

            try:
                data = await self.reader.readuntil(b'\n')
            except:
                self.hasConnection = False
                _LOGGER.error("Lost connection!")
                continue

            if data.decode().strip() is None:
                await asyncio.sleep(1)
                _LOGGER.debug("none read")
                continue
            self.parseData(data.decode())
            async with self.processed:
                self.processed.notify()

        _LOGGER.debug("Finished Readdata")
        return True

    def parseData(self, data):
        msg = ""
        _LOGGER.debug(f"Parsing received data '{data}'")
        # Selected input source
        if data[:2] == "FN":
            source_number = data[2:4]
            _LOGGER.debug(source_number)
            _LOGGER.debug(self._source_number_to_name)

            if source_number:
                self._selected_source = self._source_number_to_name.get(source_number)
                _LOGGER.debug(self._selected_source)
            else:
                self._selected_source = None

        # Power state
        elif data[:3] == "PWR":
            if (data[3] == "1") or (data[3] == "2"):  # VSX-529  uses "2" for State off
                self._power = False
            else:
                self._power = True

 
        # Is muted
        elif data[:3] == "MUT":
            if data[3] == "1":
                self._muted = False
            else:
                self._muted = True


        # Volume level
        elif data[:3] == "VOL":
            self._volume = int(data[3:6])
            _LOGGER.debug(f"Volume: {self._volume}")

        # Query source
        elif data[:3] == "RGB":
            source_number = data[3:5]
            source_name = data[6:]
            _LOGGER.debug("Source %d: %s", source_number, source_name)

            self._source_name_to_number[source_name] = source_number
            self._source_number_to_name[source_number] = source_name

        elif data[:1] == "E":
            _LOGGER.debug(f"{data[1:3]} error")

        else:
            print (data)

        if self._async_added:
            self.async_schedule_update_ha_state()

        return msg


    def telnet_command(self, command):
        _LOGGER.debug(f"Sending Command: '{command}'")

        if self.hasConnection:
            if not self.writer:
                _LOGGER.error("No writer available")
                self.hasConnection = False
                return

            try:
                 self.writer.write(command.encode("ASCII") + b"\r")
            except (ConnectionRefusedError, OSError):
                _LOGGER.error("Pioneer %s refused connection!", self._name)
                self.hasConnection = False
                return
            except:
                _LOGGER.error("Pioneer %s lost connection!", self._name)
                self.hasConnection = False
        return


    async def async_update(self):
        """Get the latest details from the device."""
        # Pioneer will send its status when it changes
        # See readdata loop
        return True

    @property
    def name(self):
        """Return the name of the device."""
        return self._name
        
    @property
    def state(self):
        """Return the state of the device."""
        if self._power:
            return STATE_ON
        return STATE_OFF

    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""
        return self._volume/MAX_VOLUME

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        return self._muted

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return self._attr_supported_features

    @property
    def source(self):
        """Return the current input source."""
        return self._selected_source

    @property
    def source_list(self):
        """List of available input sources."""
        return list(self._source_name_to_number.keys())

    def turn_off(self):
        """Turn off media player."""
        self.telnet_command("PF")

    def volume_up(self):
        """Volume up media player."""
        self.telnet_command("VU")

    def volume_down(self):
        """Volume down media player."""
        self.telnet_command("VD")

    def set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        currentlevel = int(self._volume)
        goal = int(volume * MAX_VOLUME)
        goUp = currentlevel - goal < 0

        _LOGGER.debug (f"Set volume: current {currentlevel} goal {goal} {goUp}")
        # volume Up and down change it by step 2 e.g. 0,3,5,7,..
        for x in range(abs(int((currentlevel - goal)/2))):
          if (goUp):
            self.volume_up()
          else:
            self.volume_down()

    def mute_volume(self, mute):
        """Mute (true) or unmute (false) media player."""
        self.telnet_command("MO" if mute else "MF")

    def turn_on(self):
        """Turn the media player on."""
        # See Pioneer Document page 3
        self.telnet_command("")
        time.sleep(0.1)
        self.telnet_command("\nPO")
        time.sleep(0.1)
        self.telnet_command("")
        self.telnet_command("?P")

    def select_source(self, source):
        """Select input source."""
        self.telnet_command(self._source_name_to_number.get(source) + "FN")
