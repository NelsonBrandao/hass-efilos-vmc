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
- The panel connected to your network. If there's no cable at the panel, a
  small travel router in Wi-Fi client mode next to it works well; see
  [docs/mango-setup.md](docs/mango-setup.md).
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

## Installation

### HACS

1. HACS → ⋮ → **Custom repositories** → add
   `https://github.com/NelsonBrandao/efilos-vmc`, type **Integration**.
2. Install **Efilos VMC** and restart Home Assistant.

### Manual

Copy `custom_components/efilos_vmc` into your Home Assistant
`config/custom_components/` folder and restart.

## Configuration

**Settings → Devices & services → Add integration → Efilos VMC**

1. Enter the panel's IP (or the IP of a router that forwards port 502 to
   it), port `502` and unit ID `1`.
2. Choose the fan type:
   - **Variable speed**: the panel shows the speed as a %.
   - **Three speeds**: the panel shows speeds 1, 2 and 3.
3. The fan speed feedback unit (rpm or %) is detected automatically. Change
   it if the fan speed sensors look wrong.

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
- [docs/ethernet-cabling.md](docs/ethernet-cabling.md): options for running a
  cable to the panel

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
