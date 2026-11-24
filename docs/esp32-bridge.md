# ESP32 Wi-Fi bridge behind the panel

An alternative to the travel router in [mango-setup.md](mango-setup.md):
a small ESP32 board with an Ethernet port, hidden in the wall box behind the
touch panel and powered from the panel's own 24 V. Nothing visible, no extra
cable through the wall and no mains socket needed.

> **Status: design only.** This hasn't been built or tested yet, and the
> firmware described below doesn't exist yet. The travel-router setup is the
> one that is known to work.

```
VMC main board ──3-wire bus (24 V / S / G)──> touch panel ──RJ45──> ESP32 Ethernet board
                                                    │                       │
                                          24 V ──> 5 V converter ──────────┘ (power)
ESP32 ──Wi-Fi──> home network ──> Home Assistant connects to <esp32-ip>:502
```

## Why not wire an ESP32 straight to the RJ45 jack

Ethernet needs a PHY chip and isolation transformers to drive the line. The
ESP32 has an Ethernet MAC but no PHY, so its GPIO pins can't be wired to the
jack. Use a board that already has the PHY and the jack.

## Parts

| Part | Notes |
|---|---|
| **WT32-ETH01** | ESP32 + LAN8720 PHY + RJ45, about 55 × 25 mm. Takes 5 V or 3.3 V. Alternatives: Olimex ESP32-POE-ISO, LilyGO T-ETH-Lite, or any ESP32 with a W5500 SPI module. |
| **24 V → 5 V step-down module** | Mini buck converter (for example MP1584-based, about 22 × 17 mm), set to 5.0 V, rated 1 A or more. |
| **Short Ethernet cable** | 10–15 cm slim patch cable from the panel's jack to the board's jack. |
| Heat-shrink, double-sided tape | Insulate the converter and fix everything so nothing touches the panel board. |

## Power

The panel's green terminal carries the VMC's 24 V supply (`24`, `S`,
`-`/G). The converter's input goes to `24` and `-`. Never connect anything to
`S`: that's the data line between the panel and the VMC.

| | Typical | Peak (Wi-Fi transmit) |
|---|---|---|
| WT32-ETH01 at 5 V | ~0.5–1 W | ~1.5 W |
| Current drawn from 24 V | ~30–50 mA | ~80 mA |

The manual rates the panel itself at 9–30 V DC, 250 mW, but doesn't say how
much spare current the VMC's 24 V supply has. Before installing:

1. Find the 24 V supply rating on the VMC's power supply or main board label.
   You want at least 100 mA to spare.
2. Bench-test the converter: 24 V in, 5.0–5.2 V out, before connecting the
   ESP32.
3. With everything running, measure the 24 V at the panel terminal. It
   should stay well above 20 V.

## Network layout

The ESP32 doesn't route. It works as a TCP proxy: Home Assistant connects to
the ESP32 over Wi-Fi, and the ESP32 opens its own connection to the panel
over Ethernet and passes the bytes through.

| Device | Interface | Address |
|---|---|---|
| ESP32 | Wi-Fi | DHCP from the home router, reserved (for example `192.168.1.50`) |
| ESP32 | Ethernet | static `192.168.9.1/24` |
| Panel | Ethernet | static `192.168.9.10`, mask `255.255.255.0`, gateway `192.168.9.1` |

Because the ESP32 talks to the panel from the same small subnet, the panel's
gateway setting doesn't matter for Modbus. That avoids the most common
problem with the router setup.

Set the panel's address in Menu → Installer (password `5678`) →
Communication, then Reinicialização (reset).

## Firmware

ESPHome can't be used: it runs either Wi-Fi or Ethernet, not both at once,
and has no Modbus TCP support. The firmware needs to be a small Arduino
(ESP32 core 3.x) or ESP-IDF program that:

1. Brings up Ethernet with a static IP. WT32-ETH01 settings: PHY LAN8720,
   PHY address 1, MDC GPIO23, MDIO GPIO18, PHY power GPIO16, clock input on
   GPIO0.
2. Joins the home Wi-Fi with automatic reconnect.
3. Listens on Wi-Fi port **502** and forwards each connection to
   `192.168.9.10:502`. The panel serves only **one Modbus client at a
   time**, so the proxy should allow one client and drop the old one when a
   new one connects.
4. Optionally forwards port **8080** to the panel's web page on port 80.
5. Supports OTA updates, so the board never has to come out of the wall
   again.

Home Assistant then points at the ESP32: in the Efilos VMC integration, set
the host to the ESP32's Wi-Fi IP and keep port 502.

## Fitting it behind the panel

- Measure the wall box first. A standard 60 mm round box is tight with the
  bus cable, the board, the converter and a patch cable; a rectangular or
  deeper box is easier.
- The box must be plastic. A metal box blocks the ESP32's Wi-Fi.
- Check the Wi-Fi signal at the panel before closing up. The WT32-ETH01 has
  a PCB antenna, and the panel cover and wall reduce range.
- Switch the VMC off before connecting anything to the 24 V terminal.

## Compared with the travel router

| | ESP32 behind the panel | Travel router |
|---|---|---|
| Visible hardware | None | Router plus USB charger near a socket |
| Power | Panel's 24 V bus | Mains (USB charger) |
| Setup | Custom firmware, soldering/crimping | Web UI, no code |
| Tested | No | Yes |
