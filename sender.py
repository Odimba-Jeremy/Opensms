"""Envoi réel du SMS. Seul fichier qui dépend du matériel.

Modes :
  - termux : Android + Termux + appli Termux:API  (pkg install termux-api)
  - modem  : modem USB GSM via commandes AT       (pip install pyserial)
  - mock   : affiche seulement dans la console (tests)
"""
import subprocess
import time

import config


class SenderError(Exception):
    pass


def send(number: str, message: str) -> None:
    mode = config.SENDER_MODE
    if mode == "termux":
        _send_termux(number, message)
    elif mode == "modem":
        _send_modem(number, message)
    elif mode == "mock":
        print(f"[MOCK] SMS vers {number}: {message}")
    else:
        raise SenderError(f"SMS_SENDER inconnu: {mode}")


# ---------- Termux ----------
def _send_termux(number: str, message: str) -> None:
    try:
        result = subprocess.run(
            ["termux-sms-send", "-n", number, message],
            capture_output=True, text=True, timeout=30,
        )
    except FileNotFoundError:
        raise SenderError("termux-sms-send introuvable (pkg install termux-api)")
    except subprocess.TimeoutExpired:
        raise SenderError("Timeout termux-sms-send")
    if result.returncode != 0:
        raise SenderError(result.stderr.strip() or "Échec termux-sms-send")


# ---------- Modem GSM ----------
def _read_until(ser, tokens: tuple, timeout: float) -> str:
    end = time.time() + timeout
    buf = ""
    while time.time() < end:
        data = ser.read(ser.in_waiting or 1).decode(errors="ignore")
        buf += data
        if any(t in buf for t in tokens):
            return buf
    raise SenderError(f"Timeout modem, réponse reçue: {buf!r}")


def _send_modem(number: str, message: str) -> None:
    try:
        import serial  # pyserial
    except ImportError:
        raise SenderError("pyserial manquant (pip install pyserial)")

    try:
        ser = serial.Serial(config.SERIAL_PORT, config.BAUDRATE, timeout=1)
    except serial.SerialException as e:
        raise SenderError(f"Port série inaccessible: {e}")

    try:
        ser.write(b"AT\r")
        _read_until(ser, ("OK",), 5)
        ser.write(b"AT+CMGF=1\r")  # mode texte
        _read_until(ser, ("OK",), 5)
        ser.write(f'AT+CMGS="{number}"\r'.encode())
        _read_until(ser, (">",), 10)
        ser.write(message.encode("ascii", errors="replace") + bytes([26]))  # Ctrl+Z
        resp = _read_until(ser, ("OK", "ERROR"), 30)
        if "ERROR" in resp:
            raise SenderError(f"Le modem a refusé l'envoi: {resp.strip()}")
    finally:
        ser.close()
