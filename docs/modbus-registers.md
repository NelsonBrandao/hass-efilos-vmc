# Modbus register map (Efilos Controlador TS IP)

Transcribed and translated from the manual, pages 17–19
(`efilos-controlador-ts-manual-pt.pdf`).

- All values are 16-bit holding registers (function codes 03 read, 06/16
  write, 23 read/write).
- **Numbering:** the manual uses 1-based register numbers. On the wire (and
  in Home Assistant `address:`) use **register − 1**. Tools like `mbpoll`
  use 1-based numbers by default, so pass the manual number to them.
- `Bxx` = bit xx of the register (B00 = least significant).
- R/W values reset to the panel/web-server values if no register is read for
  the disconnection timeout (default 10 s, register 8503) or if the unit
  is powered off.
- Modbus writes are blocked for 60 s after any change made in the web
  server.

## Connection defaults

| Setting | Default |
|---|---|
| Protocol | Modbus TCP (selectable: TCP-ip or RS485 via add-on card) |
| IP | 192.168.1.243 |
| Mask | 255.255.255.0 |
| Gateway | 192.168.1.1 |
| Port | 502 (standard; not stated in the manual) |
| Max simultaneous connections | 8 |
| Disconnection timeout | 10 s (reg 8503, 65535 disables) |
| RS485 (if card fitted) | 9600 baud, address 1, 1 stop bit, parity as set in the menu |
| Installer password | 5678 |

## Configuration

| Reg | Name | R/W | Meaning |
|---|---|---|---|
| 1–2 | SW_PN_0/1 | R | Software model |
| 3–4 | SW_VER (AAMM, DDPP) | R | Software version |
| 5 | REMOTE CONTROL | R/W | B00 device reset notice (default 1; reads 1 again after a reset if you wrote 0). B01 terminal connected. B02 RS485 terminal connected. B04 connection lost notice. B13 write 1 to reset the board. B14 write 1 to store configuration in NOVRAM after a write. B15 write 1 to store set-points in NOVRAM after a write. |
| 14 | SPEED_BALANCE | R/W | Fan unbalance, 67–150 % (exhaust as % of supply) |
| 20 | PARAMETER FLAGS | R/W | B00–01 season: 0 auto, 1 winter, 2 summer. B02–03 bypass: 0 auto, 1 forced off (closed), 2 forced on (open). B04 dehumidifier off. B05 fans off. B06 post-heating/cooling off. |
| 24–27 | UNIT_n_MAX_FILT_HOURS | R/W | Filter alarm threshold, 0–199 × 500 h, units 1–4 |

## Commands

| Reg | Name | R/W | Meaning |
|---|---|---|---|
| 51 | SPEED_SET_POINT | R/W | Variable speed: 0–100 %, 101 = timetable, 102 = auto. 3-speed: 1–3, 4 = timetable, 5 = auto. CAV/COP: Pa or m³/h, 65634 = timetable, 65535 = auto. |
| 52 | TEMPERATURE_SET_POINT | R/W | 0 = off, or 50–300 (×0.1 °C). Only with post-treatment. |
| 53 | TIMER | R/W | 0–14400 s at maximum fan speed (boost) |
| 54 | SPEEDS REMOTE CONTROL | R/W | B00–06 supply speed 0–100 %. B07 supply remote control enable. B08–14 exhaust speed 0–100 %. B15 exhaust remote control enable. Drives the fans independently of the control logic. |
| 55 | RHUMIDITY_SET_POINT | R/W | 0–100 %, only with dehumidify function |
| 56 | TEMPERATURE_FREE_SET_POINT | R/W | 50–400 (×0.1 °C), free cooling/heating set-point |

## Unit 1 data (read only)

| Reg | Name | Unit | Meaning |
|---|---|---|---|
| 81 | TEMP_E | 0.1 °C | Outdoor air |
| 82 | TEMP_R | 0.1 °C | Extract air (from the house) |
| 83 | TEMP_X | 0.1 °C | Exhaust air (expelled outside) |
| 84 | TEMP_I | 0.1 °C | Supply air (into the house) |
| 85 | TEMP_W | 0.1 °C | Water coil |
| 86 | STATUS_FLAGS | bits | B00 bypass open. B01 supply remote control active. B02 exhaust remote control active. B03 dehumidify on. B04 antifrost active. B05 DI humidity. B06 DI PIR. B07 DI remote off. B08 heat/cool stage 1. B09 post-heat stage 2. B10 water coil low temperature. B11 DI summer. B12 DI fire. B13 DI water antifrost. B14 DO auto compare. |
| 87 | SPEED_C | % or rpm | Supply fan speed |
| 88 | SPEED_D | % or rpm | Exhaust fan speed |
| 89 | AUTO_INPUT_VALUE | % | Air quality / humidity / 0–10 V input |
| 90 | ALARMS1 | bits | B00 X540 board comms. B01 TE probe. B02 TR probe. B03 TX probe. B04 filters clogged. B05 fan failure. B06 air quality sensor. B07 TI probe. B08 X531 board comms. B09 TW probe. B10 water coil frost. B11 quality probe timeout. B12–13 X570 board comms. B14 supply pressure sensor. B15 exhaust pressure sensor. |
| 91–92 | DP_SUPPLY / DP_EXHAUST | Pa | Pressure (COP units) |
| 93–94 | FLOW_SUPPLY / FLOW_EXHAUST | m³/h | Airflow (CAV units) |
| 95–96 | FAN_HOURS_H / _L | h | Fan running hours (high × 65536 + low) |
| 97 | ALARMS2 | bits | B00 configuration. B01 anti-ice. B02 analog input 2. B03 TD probe. B04–07 X570 extra flow boards. B08 quality probe 2 timeout. B09 running at min speed from DI. |
| 98 | PRE-HEAT | % | Pre-heating regulation |
| 99 | POST-HEAT | % | Post-heating regulation |
| 100 | TEMP_D | 0.1 °C | Air after cooling coil (dehumidify) |

Units 2–4 repeat the same layout starting at 101, 161 and 221.

## Timetable

| Reg | Meaning |
|---|---|
| 1001–1003 | Timetable speeds 0, 1, 2 (same encoding as reg 51) |
| 1017–1024 | Monday, 8 change points. B00–10 minutes since 00:00. B11–13 speed index 0–2. B14–15 temperature regulation on/off. |
| 1025–1072 | Tuesday to Sunday, same layout, 8 registers per day |

## Service

| Reg | Meaning |
|---|---|
| 8502 | RS485 baud rate (×100), default 96 |
| 8503 | Disconnection timeout in s, default 10, 65535 disables |
| 8555 | Day, 1 Monday – 7 Sunday |
| 8556 | Hour 1–24 |
| 8557 | Minutes 0–59 |
| 8559 | Installer password (5678) to unlock parameter writes |
