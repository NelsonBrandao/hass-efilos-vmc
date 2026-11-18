# My install notes (Efilos VMC → Home Assistant)

Integrate the **Efilos VMC Fluxo Duplo Air Compact 415 Lite** (with the
**Controlador TS IP App** / Evo-light touch panel) into Home Assistant over
**Modbus TCP**, using the panel's built-in Ethernet port.

No extra hardware or firmware changes: the "IP" version of the panel
already runs a Modbus TCP server and a web server.

## Status

- [x] Identify the hardware and the protocol
- [x] Home Assistant package written (`homeassistant/packages/efilos_vmc.yaml`)
- [x] Choose how to network the panel: GL.iNet Mango Wi-Fi bridge (see `docs/mango-setup.md`)
- [x] Configure the Mango (repeater + port forwards), Mango at 192.168.107.48
- [x] Enable Modbus TCP and set the IP on the panel (192.168.8.10 behind the Mango)
- [x] Verify register reads with `mbpoll` (2026-11-18: temps 16.6 / 19.4 / 18.1 / 19.6 °C)
- [x] Confirm fan type: variable speed (reg 51 = 35 %), fan speed regs report rpm
- [x] Install the package in Home Assistant (working 2026-11-18)

### Physical install (remaining)

Plan: Mango in the roof space next to the VMC, powered from a USB charger
on the socket there. One Ethernet cable runs through the existing VMC
conduit down to the panel. No 24 V tapping, nothing extra in the wall box.

- [ ] Wi-Fi test first: put the Mango in the roof on a charger, check the signal on its Repeater page and leave HA running on it for a day
- [x] Confirm the conduit only carries the low-voltage bus cable (no mains in the same pipe): only the 3-wire panel bus (24 V / S / G)
- [ ] Measure the run length (panel → roof) and add ~1 m slack each end
- [ ] Cable: Cat6 U/UTP (unshielded, thinner); slim Cat6 if the pipe is tight
- [ ] Pull with a pull string alongside the bus cable; never pull on the bus cable itself
- [ ] Panel end: crimp an RJ45 plug (pass-through plugs are easiest), leave enough slack to take the panel off the wall
- [ ] Roof end: crimp a plug or use a keystone + short patch cable into the Mango LAN port
- [ ] Test the cable with a tester before plugging in (all 8 pins, or at least 1-2-3-6)
- [ ] Mount the Mango off the roof underside, in shade and away from dust (roof spaces get hot in summer)
- [ ] Use a decent 5 V / 2 A USB charger; label the plug "VMC network — do not unplug"
- [ ] Close up the panel, then check HA stays available for a day

### Clean-up (remaining)

- [ ] Mango: export a config backup (System → Backup), note the admin password in your password manager
- [ ] Home router: confirm the Mango's DHCP reservation (192.168.107.48)
- [ ] HA: assign the VMC entities to an area, hide the `*_raw` sensors, add a dashboard card
- [ ] HA: remove the airflow sensors if they stay at 0 (no CAV/COP kit)
- [ ] Optional: copy the package into your HA config repo / homelab backups

## Hardware

Photo: `docs/panel-board.jpg`

| Part | What it is |
|---|---|
| STM32F107 (centre right) | Main MCU, has a built-in Ethernet MAC |
| QFP chip next to the jack | Ethernet PHY |
| RJ45 jack (bottom left, under the white sticker) | **Ethernet port** for Modbus TCP and the web server |
| Green 3-screw terminal (top left) | Bus to the VMC main board: `24` (24 V), `S` (signal), `-`/G (ground). Leave it alone. |
| CR2032 holder | Clock backup battery (timetable) |
| Sticker `NTCPIP…` | Serial / part number of the TCP/IP version |

The "XBUS - S 24" text on the sticker describes the green terminal's
pinout. The jack itself is plain 10/100 Ethernet (no PoE).

## Network setup on the panel

1. Menu → **Installer** (password `5678`) → **Communication**.
2. **Modbus**: TCP-ip.
3. **IP0–IP3**: a free static IP on your LAN (default 192.168.1.243).
4. **NM0–NM3**: subnet mask (default 255.255.255.0).
5. **GW0–GW3**: gateway (default 192.168.1.1).
6. **Reinicialização** (reset) to apply without a power cycle.
7. Reserve that IP in your router's DHCP so nothing else takes it.

## Verify from a computer

```bash
brew install mbpoll
```

```bash
mbpoll -a 1 -r 81 -c 4 -t 4 -1 192.168.1.243
```

Expect four values in tenths of a degree (outdoor, extract, exhaust,
supply). `mbpoll` uses the manual's 1-based register numbers.

Web server: `http://<panel-ip>`.

## Home Assistant

1. In `configuration.yaml`:
   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```
2. Copy `homeassistant/packages/efilos_vmc.yaml` to `/config/packages/`.
3. Change `host:` to the panel IP.
4. Restart Home Assistant.

Entities created:

| Entity | Purpose |
|---|---|
| `fan.vmc` | On/off, speed 0–100 %, presets Schedule / Auto |
| `select.vmc_bypass_mode` | Auto / Closed / Open |
| `select.vmc_season` | Auto / Winter / Summer |
| `sensor.vmc_*_air_temperature` | Outdoor, extract, exhaust, supply |
| `sensor.vmc_supply_fan_speed`, `sensor.vmc_extract_fan_speed` | Actual fan speeds |
| `sensor.vmc_fan_running_hours` | Total fan hours |
| `binary_sensor.vmc_filter_alarm` | Filter change needed |
| `binary_sensor.vmc_fan_failure`, `binary_sensor.vmc_any_alarm` | Faults |
| `binary_sensor.vmc_bypass_open`, `binary_sensor.vmc_antifrost_active` | Status |

## Gotchas

- **Address offset:** HA `address:` = manual register − 1.
- **10 s timeout:** values written over Modbus are dropped if nothing reads
  a register for 10 s. The package polls every 5 s. If HA goes down, the
  VMC reverts to the panel's settings.
- **Web server lock:** a change made in the web server blocks Modbus writes
  for 60 s.
- **Fan type:** the package assumes variable-speed (EC) fans. If the panel
  shows speeds 1/2/3, register 51 takes 1–3 (4 = timetable, 5 = auto) and
  the fan entity needs adapting.
- **Fan speed sensors** report rpm on this unit (confirmed 2026-11-18:
  supply 1469, extract 1500 at 35 %).
- **Airflow sensors** only work with a CAV/COP kit; remove them if they
  stay at 0.

## Files

| Path | Content |
|---|---|
| `homeassistant/packages/efilos_vmc.yaml` | Home Assistant package |
| `docs/modbus-registers.md` | Full register map in English |
| `docs/mango-setup.md` | GL.iNet Mango Wi-Fi bridge setup (chosen approach) |
| `docs/ethernet-cabling.md` | Options for getting a cable to the panel |
| `docs/efilos-controlador-ts-manual-pt.pdf` | Original manual (Portuguese) |
| `docs/panel-board.jpg` | Photo of the panel board |
