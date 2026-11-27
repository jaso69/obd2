OBD2DESK FOR LINUX
==================

Car diagnostics: VAG KW1281 with a KKL 409.1 cable (SEAT/VW/Audi/Skoda up to
~2004) and generic OBD2 with an ELM327 (USB, Bluetooth or WiFi), with an AI
assistant. English and Spanish interface (selector next to the program name).

Works on 64-bit distributions (x86_64) with glibc 2.31 or later:
Ubuntu 20.04+, Debian 11+, Linux Mint 20+, Fedora, openSUSE, Arch...


INSTALL (no sudo)
-----------------
    ./instalar.sh

Copies the program to ~/.local/bin and adds it to the applications menu as
"OBD2Desk". You can also run it directly: ./OBD2Desk

Uninstall: ./instalar.sh --desinstalar


PERMISSION FOR THE CABLE (once)
-------------------------------
To open the KKL cable or the ELM327 your user must be in the serial port
group (the installer tells you which one):

    sudo usermod -aG dialout $USER        (Ubuntu, Debian, Mint, Fedora...)
    sudo usermod -aG uucp $USER           (Arch, Manjaro)

then log out and back in.

Ubuntu/Mint: if /dev/ttyUSB0 doesn't appear when you plug in the cable, the
culprit is usually brltty (braille display service). If you don't use it:
sudo apt remove brltty


PORTS
-----
- KKL cable (FTDI) and USB ELM327: /dev/ttyUSB0 (or /dev/ttyACM0).
- Bluetooth ELM327: /dev/rfcomm0, after pairing it and creating the port
  (see below).
- WiFi ELM327: connect to the adapter's WiFi network and choose
  "WiFi · 192.168.0.10:35000" (or type ip:port).
- "Simulator (no car)" to try the program with nothing connected.


CONNECTING A BLUETOOTH ELM327
-----------------------------
A Bluetooth ELM327 works like a wireless serial cable: the system gives it a
virtual serial port (/dev/rfcomm0) and the program talks to it just like a
USB adapter. So in the program you don't look for "Bluetooth": you choose
that port. First pair it in the system, then connect from the program.

1. Plug the ELM327 into the car and switch on the ignition (its light comes on).
2. Pair it from your desktop's Bluetooth settings or with:
       bluetoothctl
         scan on                  (find the MAC: it usually shows as OBDII)
         pair AA:BB:CC:DD:EE:FF   (usual PIN: 1234, 0000 or 6789)
         trust AA:BB:CC:DD:EE:FF
         quit
3. Linux doesn't create the port by itself. Create it with:
       sudo rfcomm bind 0 AA:BB:CC:DD:EE:FF
   /dev/rfcomm0 appears. Repeat this after each reboot.
4. In the program: Connection "ELM327", Port "/dev/rfcomm0" and Connect.

If you don't have the rfcomm command: Fedora -> sudo dnf install
bluez-deprecated; Arch -> bluez-deprecated-tools. On Debian, Ubuntu and Mint
it comes with bluez.

An ELM327 accepts only one connection at a time: close the phone app
(Torque, Car Scanner...) or turn off its Bluetooth before connecting from
the computer.


DATA
----
- Settings and AI API key: ~/.config/OBD2Desk/config.json
  (readable only by your user).
- CSV recordings and reports: Documents/OBD2Desk folder.

Website: https://obd2desk.com
Code, help and new versions: https://github.com/jaso69/obd2
MIT license (see LICENSE).
