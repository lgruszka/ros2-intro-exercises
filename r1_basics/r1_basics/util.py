"""Wspólne funkcje bez zależności od ROS (testowalne zwykłym pytest).

Kąty w radianach, prędkości w m/s i rad/s, ramy jak w REP 103 (x do przodu, y w lewo, z w górę).
"""
import math


def clamp(value, low, high):
    """Przytnij value do przedziału [low, high]."""
    return max(low, min(high, value))


def wrap_angle(angle):
    """Kąt sprowadzony do przedziału (-pi, pi]."""
    return math.atan2(math.sin(angle), math.cos(angle))


def yaw_to_quat(yaw):
    """Kwaternion (x, y, z, w) obrotu o yaw wokół osi z (kolejność jak w geometry_msgs)."""
    return (0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0))


def quat_to_yaw(x, y, z, w):
    """Kurs (yaw) z kwaternionu (x, y, z, w)."""
    return math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


def limit_vector(vx, vy, max_v):
    """Skaluje wektor (vx, vy) tak, żeby jego długość nie przekroczyła max_v (kierunek bez zmian)."""
    norm = math.hypot(vx, vy)
    if norm <= max_v or norm == 0.0:
        return vx, vy
    scale = max_v / norm
    return vx * scale, vy * scale


def holonomic_p_control(dx, dy, yaw, k_lin, k_yaw, max_v, max_wz, yaw_stop_dist=0.25):
    """Regulator P dojazdu do punktu dla robota holonomicznego (R1 idzie też bokiem).

    dx, dy: błąd pozycji w ramie odom (cel minus robot), yaw: kurs robota w odom.
    Zwraca (vx, vy, wz) w ramie robota:
      - błąd obrócony do ramy robota, vx = k_lin*ex, vy = k_lin*ey, wektor przycięty do max_v,
      - wz = k_yaw * (kąt do celu w ramie robota), przycięte do max_wz; blisko celu (< yaw_stop_dist)
        wz = 0, bo kierunek do celu zaczyna tam skakać i robot kręciłby się w miejscu.
    """
    c, s = math.cos(yaw), math.sin(yaw)
    ex = c * dx + s * dy
    ey = -s * dx + c * dy
    vx, vy = limit_vector(k_lin * ex, k_lin * ey, max_v)
    if math.hypot(dx, dy) < yaw_stop_dist:
        wz = 0.0
    else:
        wz = clamp(k_yaw * math.atan2(ey, ex), -max_wz, max_wz)
    return vx, vy, wz


def integrate_body_velocity(x, y, heading, vx, vy, dt):
    """Jeden krok odometrii zliczeniowej: prędkość (vx, vy) w ramie robota -> nowa pozycja w odom."""
    c, s = math.cos(heading), math.sin(heading)
    return x + (vx * c - vy * s) * dt, y + (vx * s + vy * c) * dt
