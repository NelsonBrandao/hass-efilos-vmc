# GL.iNet Mango (GL-MT300N-V2) as Wi-Fi bridge for the panel

The Mango joins the home Wi-Fi as a client ("repeater") and gives the panel
a wired port on its own small network. Home Assistant reaches the panel
through two port forwards on the Mango.

```
VMC panel RJ45 ──patch cable──> Mango LAN port
Mango ──Wi-Fi (repeater)──> home router ──> Home Assistant
HA connects to <mango-ip>:502   →  forwarded to 192.168.8.10:502 (panel)
browser   <mango-ip>:8080       →  forwarded to 192.168.8.10:80  (panel web page)
```

Addresses used below:

| Device | Address |
|---|---|
| Mango admin page (its own network) | 192.168.8.1 |
| Panel (static, outside the Mango's DHCP pool 192.168.8.100–249) | 192.168.8.10 |
| Mango on the home network | whatever the home router gives it, then reserved |

Menu names are for GL.iNet firmware v4. Older v3 firmware has the same
features under slightly different menus.

## 1. Configure the Mango at your desk

1. Power it from a USB charger (micro-USB, 5 V).
2. Join its Wi-Fi (`GL-MT300N-V2-xxx`, password on the label) or plug a
   laptop into its LAN port.
3. Open `http://192.168.8.1`, choose the language and set an admin password.
4. **System → Upgrade**: install the latest firmware.
5. **Internet → Repeater → Connect**: pick your home Wi-Fi, enter its
   password, Apply. A green dot means it's connected.
6. On your home router, find the Mango in the client list and give it a
   **DHCP reservation**, so its IP never changes. Call this `<mango-ip>`.
7. **Network → Firewall → Port Forwarding → Add**:

   | Name | Protocol | External port | Internal IP | Internal port |
   |---|---|---|---|---|
   | vmc-modbus | TCP | 502 | 192.168.8.10 | 502 |
   | vmc-web | TCP | 8080 | 192.168.8.10 | 80 |

   The source/external zone is WAN; the repeater uplink belongs to it.
8. **Wireless**: keep the Mango's own access point on with a strong
   password. It's the easy way back into the admin page later, since the
   admin page isn't reachable from the home network. Optionally hide its
   SSID.
9. Turn off anything you don't need (GoodCloud, VPN, AdGuard).

Optional: **Internet → Ethernet → change WAN to LAN** so either port works
for the panel. Keep the WAN port unplugged while changing it.

## 2. Set the panel's network address

On the touch panel: Menu → **Installer** (password `5678`) →
**Communication**:

| Setting | Value |
|---|---|
| Modbus | TCP-ip |
| IP0.IP1.IP2.IP3 | 192.168.8.10 |
| NM0–NM3 | 255.255.255.0 |
| GW0–GW3 | 192.168.8.1 |

Then **Reinicialização** (reset) to apply.

## 3. Connect and test

1. Plug the panel's RJ45 into the Mango's LAN port.
2. In the Mango admin page, **Clients** should list a wired device at
   192.168.8.10.
3. From a computer on the home network:

   ```bash
   mbpoll -a 1 -r 81 -c 4 -t 4 -1 <mango-ip>
   ```

   Four temperatures in tenths of a degree means it works.
4. Browser: `http://<mango-ip>:8080` shows the panel's web page.
5. In `homeassistant/packages/efilos_vmc.yaml` set `host: <mango-ip>`
   (port stays 502), copy it to `/config/packages/`, restart HA.

## 4. Powering it from inside the wall box

The Mango only takes 5 V on micro-USB. The power available behind the panel
is the 24 V bus terminal.

- Use a 24 V → 5 V step-down module rated **at least 2 A** with a USB or
  micro-USB output, wired to the panel terminal's `24` and `-`.
- Expect roughly 1.5–2.5 W, so about 0.1 A extra on the 24 V line.
- Check the VMC's 24 V supply rating first (label on the VMC's power supply
  or main board). The manual doesn't state spare capacity.
- Measure the 24 V at the panel terminal with the Mango running. It should
  stay well above 20 V; the panel accepts 9–30 V.
- The Mango is about 58 × 58 × 25 mm. Make sure it, the converter and a
  short patch cable fit, and that the wall box is plastic (metal blocks
  Wi-Fi).

Test everything on a USB charger first, then move to 24 V power.

## Troubleshooting

| Symptom | Check |
|---|---|
| Mango shows no wired client | Cable seated, panel IP/mask set and reset done, panel set to TCP-ip |
| Client shows, but mbpoll times out | Port forward internal IP matches the panel; rule is TCP 502 |
| Works, then drops after home router reboot | Repeater reconnects by itself within a minute; check the Mango's DHCP reservation on the home router |
| HA entities flip unavailable | Weak Wi-Fi in the wall box; check signal in the Mango's Repeater section |
