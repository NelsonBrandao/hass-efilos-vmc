# Getting Ethernet to the touch panel

The panel's RJ45 jack is the only network interface (no Wi-Fi). It needs a
plain 10/100 Ethernet link to your LAN. Bandwidth is irrelevant: Home
Assistant polls a few registers every 5 s, so any link that stays up works.

Do **not** use PoE on this port. The board is powered from the 24 V bus
terminal and has no PoE circuitry.

## Before choosing an option

1. **Look at how the 3-wire bus cable reaches the panel.** Remove the panel
   from the wall and check whether the bus cable runs inside a corrugated
   conduit (tubo VD / anelado) or is buried straight in the wall.
2. **Find where that conduit goes.** It ends at the VMC unit (ceiling or
   attic). Check whether there is a junction box on the way, or whether
   the conduit passes near an ITED telecom box or a room with a network
   point.
3. **Measure free space in the conduit.** A 20 mm conduit holding one thin
   3-wire cable usually has room for one Cat6 cable (about 6 mm diameter).
   A 16 mm conduit is tight but often works with slim Cat6 (about 4 mm).

## Options, best first

### 1. Run Cat6 through the existing bus conduit

Most reliable result, nothing visible on the wall.

- Feed a pull wire (fish tape / guia passa-fios) through the conduit
  alongside the bus cable. Never use the bus cable itself to pull: if it
  breaks, the panel loses power and contact with the VMC.
- Pull a Cat6 (solid or slim patch) cable to the nearest place with network
  access: the VMC location, an attic, or the ITED box.
- At the panel end, a short patch cable or a crimped RJ45 plug goes into
  the board's jack. Leave enough slack to take the panel off the wall.
- Cutting a small notch in the plastic case may be needed for the plug to
  fit with the case closed.

### 2. Surface raceway (calha) from the nearest network point

Use this if the conduit is full or not continuous.

- Self-adhesive white raceway along the skirting board or ceiling corner
  from the nearest router, switch, or wall network socket.
- Slim flat Cat6 cable fits in the smallest raceway sizes.
- Cheap and fully reversible; it is visible, though.

### 3. Wi-Fi to Ethernet bridge next to the panel

Use this if no cable route is practical.

- A small travel router in client/WISP mode (for example a GL.iNet
  Mango/Opal class device) or any "Wi-Fi to Ethernet adapter" gives the
  panel a wired port while the bridge itself joins your Wi-Fi.
- It needs 5 V USB power near the panel: a nearby socket, or a flush USB
  socket in the same wall box if there is mains power behind it.
- Give the bridge and the panel fixed IPs (DHCP reservation for the bridge,
  static IP set in the panel's Communication menu).
- Do not power the bridge from the panel's 24 V bus without knowing the
  VMC's power budget: the panel itself only draws about 250 mW, and the
  VMC's 24 V supply was not designed with an extra load in mind.

### 4. Powerline adapter

Use this if there is a mains socket near the panel and Wi-Fi is weak there.

- One adapter at the router, one in the socket near the panel, short patch
  cable to the panel. Works through house wiring; quality depends on the
  installation (RCD/breaker circuits can reduce throughput, which does not
  matter for Modbus).

## Alternative: move the panel closer to the network

The manual allows up to **70 m** between the panel and the VMC's main board
over the 3-wire bus. If there is a better spot for the panel next to a
network point, extending the bus cable (0.3 mm² minimum, shielded
recommended) is another route. You lose the panel at its current location,
so this only makes sense if the current spot is not important.

## After the cable is in

1. Plug in and check the jack's link LEDs (if fitted) or your switch's port
   status.
2. On the panel: Menu → Installer (password `5678`) → Communication →
   Modbus = TCP-ip, set IP / mask / gateway, then Reset.
3. From a computer on the same network: open `http://<panel-ip>` (built-in
   web server) or run `mbpoll -a 1 -r 81 -c 4 -t 4 -1 <panel-ip>`.
4. Continue with the Home Assistant steps in the README.
