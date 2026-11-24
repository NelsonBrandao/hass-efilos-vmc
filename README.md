# Efilos VMC for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)

Local control of **Efilos** heat-recovery ventilation units (VMC de fluxo
duplo) that use the **Controlador TS IP** touch panel, over **Modbus TCP**.
No cloud, no extra hardware: the IP version of the panel already has an
Ethernet port with a Modbus TCP server.

Tested with an **Air Compact 415 Lite** (variable-speed fans). Other Efilos
units with the same "Controlador TS IP" panel use the same register map and
should work. Reports for other models are welcome.

## Features

| Entity | What it does |
|---|---|
| Fan | On/off, speed 1–100 % (or 1/2/3 on three-speed units), presets **Schedule** (panel timetable) and **Auto** (air-quality sensor) |
| Select: Bypass | Auto / Closed / Open |
| Select: Season | Auto / Winter / Summer |
| Sensors | Outdoor, extract, exhaust and supply air temperature; supply and exhaust fan speed; fan running hours |
| Binary sensors | Filter alarm, fan failure, any other alarm (with the active alarm names as an attribute), bypass open, antifrost |
| Optional sensors (disabled by default) | Water coil temperature, air-quality input, pressures and airflows (CAV/COP units), pre/post-heating |

All entities belong to one device, set up from the UI.

## Requirements

- An Efilos VMC with the **Controlador TS IP** panel (the board has an RJ45
  jack; the serial sticker reads `NTCPIP…`).
- The panel connected to your network. If there's no cable at the panel,
  bridge it to Wi-Fi: a travel router in client mode
  ([docs/mango-setup.md](docs/mango-setup.md)) or an ESP32 Ethernet board
  hidden behind the panel ([docs/esp32-bridge.md](docs/esp32-bridge.md)).
- Home Assistant 2025.8 or newer.

## Panel setup

On the touch panel: **Menu → Installer** (password `5678`) →
**Communication**:

1. **Modbus**: `TCP-ip`
2. **IP0–IP3**, **NM0–NM3**, **GW0–GW3**: a free static IP, mask and gateway
   on your network (factory default `192.168.1.243` / `255.255.255.0` /
   `192.168.1.1`).
3. **Reinicialização** (reset) to apply.

Check from a computer: open `http://<panel-ip>` (the panel's own web page)
or read the temperatures:

```bash
mbpoll -a 1 -r 81 -c 4 -t 4 -1 <panel-ip>
```

Or run the read-only probe in this repo, which uses the integration's own
client and prints the decoded values:

```bash
python3 -I scripts/probe.py <panel-ip>
```

These checks only work while nothing else is connected to the panel (see
[One Modbus client at a time](#one-modbus-client-at-a-time)).

## Installation

### HACS

1. HACS → ⋮ → **Custom repositories** → add
   `https://github.com/NelsonBrandao/hass-efilos-vmc`, type **Integration**.
2. Install **Efilos VMC** and restart Home Assistant.

### Manual

Copy `custom_components/efilos_vmc` into your Home Assistant
`config/custom_components/` folder and restart.

## Configuration

**Settings → Devices & services → Add integration → Efilos VMC**

1. Enter the panel's IP (or the IP of a router that forwards port 502 to
   it), port `502` and unit ID `1`.
2. **How the fan speed is set**:
   - **Variable speed**: the panel shows the speed as a %.
   - **Three speeds**: the panel shows speeds 1, 2 and 3.
3. **Unit of the fan speed sensors**: rpm or %. This only affects the two
   fan speed sensors, not how you control the fan. It's detected from the
   current reading; choose rpm if those sensors show values in the
   hundreds or thousands.

Both choices can be changed later under **Configure**. The IP can be
changed with **Reconfigure**.

## How it behaves

- **Polling:** every 5 seconds. The controller drops values written over
  Modbus if no register is read for 10 seconds (its "Conn. a(s)" setting),
  so frequent polling keeps your changes active.
- **If Home Assistant stops:** within about 10 seconds the unit goes back to
  the settings on the touch panel. This is the controller's own safety
  behaviour.
- **Web page lock:** a change made on the panel's web page blocks Modbus
  writes for 60 seconds.
- **Fan off:** uses the controller's "fans off" flag, so the panel shows
  the unit as off as well.
- **Changing one setting keeps the others:** bypass, season and on/off all
  live in one register; the integration only changes the bits it needs.

### One Modbus client at a time

The manual says the controller accepts 8 simultaneous Modbus TCP
connections, but in practice it serves only one. While Home Assistant is
connected, any other client (mbpoll, `scripts/probe.py`, a second
integration) connects and is immediately reset with "Connection reset by
peer".

- Run only one of: this integration, Home Assistant's YAML `modbus:` setup,
  or any other Modbus tool. When moving from a YAML setup to this
  integration, remove the YAML in the same restart.
- To test with mbpoll or the probe, disable the integration first
  (**Settings → Devices & services → Efilos VMC → ⋮ → Disable**).

## Not supported yet

- Constant-airflow / constant-pressure (CAV/COP) speed control in Pa or m³/h
- Editing the weekly timetable, temperature and humidity set-points, boost
  timer
- Modbus RTU (RS485)

## Documentation

- [docs/modbus-registers.md](docs/modbus-registers.md): the controller's full
  register map, translated to English
- [docs/mango-setup.md](docs/mango-setup.md): networking the panel over Wi-Fi
  with a GL.iNet travel router
- [docs/esp32-bridge.md](docs/esp32-bridge.md): an ESP32 Ethernet board
  behind the panel as a Wi-Fi bridge, powered from the panel's 24 V

## Development

```bash
uv sync
```

```bash
uv run pytest
```

The tests run the integration against a small fake controller
(`tests/fake_vmc.py`) seeded with values read from a real unit.

## Disclaimer

Not affiliated with or endorsed by Efilos. Use at your own risk; writing
the wrong values to a ventilation unit's controller can change how it
runs.

## License

MIT
