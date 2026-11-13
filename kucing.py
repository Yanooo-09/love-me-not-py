
import math
import random
import pygame


W, H, SCALE = 160, 240, 3    
FPS = 30
LOOP = 14.0                    

GY = 206                      
FX, FY = 82, 108              
NP = 9                         
PETAL_ANG = [0.2 + k * 2 * math.pi / NP for k in range(NP)]
ORDER = [0, 4, 1, 5, 2, 6, 3, 7, 8]   
T0, STEP, FALL_T = 1.2, 0.95, 1.5     

SKY = [(10, 12, 50), (26, 28, 95), (58, 48, 135), (120, 80, 160)]
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
BAYER = [[v / 16.0 for v in row] for row in BAYER]


def lerp(a, b, t):
    return a + (b - a) * t


def build_background():
    s = pygame.Surface((W, H))
   
    for y in range(H):
        pos = min(y / 190.0, 0.999) * (len(SKY) - 1)
        i = int(pos)
        f = pos - i
        for x in range(W):
            use_next = f > BAYER[y % 4][x % 4]
            s.set_at((x, y), SKY[i + 1 if use_next else i])
    # bulan + glow dither
    mx, my = 128, 44
    for y in range(my - 34, my + 34):
        for x in range(mx - 34, mx + 34):
            if 0 <= x < W and 0 <= y < H:
                r = math.hypot(x - mx, y - my)
                if 13 < r < 34:
                    p = (1 - (r - 13) / 21.0) * 0.55
                    if p > BAYER[y % 4][x % 4]:
                        s.set_at((x, y), (110, 115, 190))
    pygame.draw.circle(s, (238, 232, 170), (mx, my), 12)
    pygame.draw.circle(s, (252, 248, 205), (mx, my), 9)
    for cx, cy, r in [(mx - 3, my + 3, 3), (mx + 4, my - 4, 2), (mx + 3, my + 5, 2)]:
        pygame.draw.circle(s, (232, 226, 170), (cx, cy), r)

    # bukit dengan shading dither
    def hill(base, amp, per, ph, c1, c2):
        for x in range(W):
            y1 = base + int(amp * math.sin(x / per + ph))
            for y in range(y1, H):
                k = min((y - y1) / 22.0, 1)
                s.set_at((x, y), c2 if k > BAYER[y % 4][x % 4] else c1)

    hill(172, 9, 23, 0.5, (44, 48, 112), (32, 38, 92))
    hill(188, 6, 14, 2.0, (30, 40, 88), (22, 32, 72))

    # tanah
    for y in range(GY, H):
        for x in range(W):
            c = (28, 92, 42) if (x + y) % 7 else (34, 104, 48)
            if (y - GY) > 8 and BAYER[y % 4][x % 4] < 0.35:
                c = (22, 76, 36)
            s.set_at((x, y), c)
    return s


# ---------------------------------------------------------------- kelopak
def make_petal(color, edge):
    p = pygame.Surface((44, 44), pygame.SRCALPHA)
    pygame.draw.ellipse(p, edge, (4, 15, 36, 14))
    pygame.draw.ellipse(p, color, (5, 16, 34, 12))
    pygame.draw.line(p, edge, (10, 22), (32, 22))
    return p


def blit_rot(surf, img, cx, cy, deg):
    r = pygame.transform.rotate(img, deg)
    surf.blit(r, (int(cx - r.get_width() / 2), int(cy - r.get_height() / 2)))


def landing_spot(k):
    """Posisi & sudut tiap kelopak setelah mendarat (di tanah, tidak kena kucing)."""
    lx = 58 + (k * 37) % 86
    ly = GY + 9 + (k * 5) % 8
    ang = ((k * 53) % 50) - 25 + (180 if k % 2 else 0)
    return lx, ly, ang


# ---------------------------------------------------------------- teks
_text_cache = {}


def text_surface(font, msg, col, shadow):
    key = (msg, col)
    if key not in _text_cache:
        a = font.render(msg, False, col)
        b = font.render(msg, False, shadow)
        out = pygame.Surface((a.get_width() + 1, a.get_height() + 1), pygame.SRCALPHA)
        out.blit(b, (1, 1))
        out.blit(a, (0, 0))
        if out.get_width() > W - 6:                       # jaga supaya muat
            nh = int(out.get_height() * (W - 6) / out.get_width())
            out = pygame.transform.scale(out, (W - 6, nh))
        _text_cache[key] = out
    return _text_cache[key]


# ---------------------------------------------------------------- hati & zZ
def draw_heart(surf, hx, hy, alpha):
    h = pygame.Surface((9, 8), pygame.SRCALPHA)
    c = (235, 70, 110, alpha)
    pygame.draw.rect(h, c, (0, 0, 3, 3))
    pygame.draw.rect(h, c, (4, 0, 3, 3))
    pygame.draw.rect(h, c, (0, 2, 7, 2))
    pygame.draw.rect(h, c, (1, 4, 5, 1))
    pygame.draw.rect(h, c, (2, 5, 3, 1))
    pygame.draw.rect(h, c, (3, 6, 1, 1))
    surf.blit(h, (int(hx) - 3, int(hy) - 2))


def draw_z(surf, x, y, s, alpha):
    z = pygame.Surface((s + 2, s + 2), pygame.SRCALPHA)
    c = (235, 235, 255, alpha)
    pygame.draw.line(z, c, (0, 0), (s, 0))
    pygame.draw.line(z, c, (s, 0), (0, s))
    pygame.draw.line(z, c, (0, s), (s, s))
    surf.blit(z, (int(x), int(y)))


# ---------------------------------------------------------------- kucing oren
def draw_cat(surf, t):
    k = 0.78                      # ukuran kucing (makin kecil = makin mungil)
    ox = 4
    oy = 233 - 22 * k             # alas badan nempel di bawah layar

    def X(v):
        return int(round(ox + v * k))

    def Y(v):
        return int(round(oy + v * k))

    def ell(x0, y0, x1, y1, c):
        a, b, cc, d = X(x0), Y(y0), X(x1), Y(y1)
        pygame.draw.ellipse(surf, c, (a, b, max(2, cc - a), max(2, d - b)))

    def poly(pts, c):
        pygame.draw.polygon(surf, c, [(X(px), Y(py)) for px, py in pts])

    O = (242, 142, 42)
    OD = (196, 98, 26)
    OL = (255, 190, 105)
    WH = (255, 236, 214)
    PK = (255, 140, 150)

    breath = 0.5 + 0.5 * math.sin(t * 2.2)          # napas pelan
    b = int(round(breath * 2))

    # ekor melingkar, bergoyang
    sw = math.sin(t * 1.3) * 0.5
    tail = []
    for i in range(15):
        a = math.radians(95 + i * 14 + sw * 10 * (i / 14.0))
        tail.append((10 + 12.6 * math.cos(a), 16 + 9 * math.sin(a)))
    for (tx, ty) in tail:
        pygame.draw.circle(surf, O, (X(tx), Y(ty)), 2)
    pygame.draw.circle(surf, OD, (X(tail[-1][0]), Y(tail[-1][1])), 2)

    # badan
    ell(2, 4 - b, 36, 22, O)
    ell(4, 12, 34, 22, OD)
    ell(6, 5 - b, 28, 11 - b, OL)
    for sx in (9, 15, 21, 27):
        pygame.draw.line(surf, OD, (X(sx), Y(5 - b)), (X(sx + 1), Y(11)))

    # kepala
    hy = 6
    ell(26, hy, 46, hy + 16, O)
    ell(28, hy + 9, 44, hy + 16, WH)
    tw = 1 if int(t * 10) % 47 < 2 else 0           # telinga sesekali kedut
    poly([(28, hy + 3), (29, hy - 5 - tw), (34, hy + 1)], O)
    poly([(39, hy + 1), (43, hy - 5), (45, hy + 4)], O)
    poly([(29, hy + 1), (30, hy - 2 - tw), (32, hy + 1)], PK)
    poly([(41, hy), (43, hy - 2), (43, hy + 2)], PK)
    # mata tertutup (pixel)
    for ex in (X(31), X(38)):
        ey = Y(hy + 6)
        surf.set_at((ex, ey), (40, 22, 18))
        surf.set_at((ex + 1, ey + 1), (40, 22, 18))
        surf.set_at((ex + 2, ey), (40, 22, 18))
    surf.set_at((X(36.5), Y(hy + 10)), PK)            # hidung

    # kaki depan putih
    ell(22, 15, 36, 22, WH)
    pygame.draw.line(surf, (225, 200, 180), (X(28), Y(17)), (X(28), Y(21)))

    # "z z" melayang naik
    for i in range(3):
        ph = ((t * 0.45) + i / 3.0) % 1.0
        zx = X(48) + ph * 14 + math.sin(ph * 6 + i) * 2
        zy = Y(-2) - ph * 24
        s = 3 + int(ph * 4)
        al = int(255 * (1 - ph) ** 0.8)
        draw_z(surf, zx, zy, s, al)


# ---------------------------------------------------------------- render 1 frame
def render(canvas, t, A):
    canvas.blit(A["bg"], (0, 0))

    # bintang berkedip
    for (x, y, p) in A["stars"]:
        tw = math.sin(t * 2 + p)
        c = (255, 255, 255) if tw > 0.3 else ((170, 175, 230) if tw > -0.5 else (90, 90, 160))
        canvas.set_at((x, y), c)
        if tw > 0.9 and p > 3:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                canvas.set_at((x + dx, y + dy), c)

    sway = math.sin(t * 1.1) * 1.5
    fcx = FX + sway

    # batang & daun
    span = GY + 4 - FY
    for y in range(FY, GY + 4):
        u = (y - FY) / float(span)
        x = FX + sway * (1 - u) ** 1.6
        pygame.draw.rect(canvas, (44, 150, 66), (int(x), y, 2, 1))
        canvas.set_at((int(x) + 2, y), (90, 200, 100))
    pygame.draw.polygon(canvas, (52, 168, 74), [(FX, 186), (FX - 20, 172), (FX - 22, 178), (FX - 6, 190)])
    pygame.draw.line(canvas, (110, 214, 120), (FX, 186), (FX - 18, 174))
    pygame.draw.polygon(canvas, (52, 168, 74), [(FX, 196), (FX + 20, 187), (FX + 22, 193), (FX + 4, 201)])
    pygame.draw.line(canvas, (110, 214, 120), (FX, 196), (FX + 18, 189))

    # kelopak yang masih menempel
    for rank, k in enumerate(ORDER):
        if t < T0 + rank * STEP:
            a = PETAL_ANG[k]
            blit_rot(canvas, A["petal"], fcx + 13 * math.cos(a), FY + 13 * math.sin(a), -math.degrees(a))

    # pusat bunga
    pygame.draw.circle(canvas, (168, 98, 20), (int(fcx), FY), 9)
    pygame.draw.circle(canvas, (236, 150, 32), (int(fcx), FY), 8)
    pygame.draw.circle(canvas, (255, 196, 70), (int(fcx) - 2, FY - 2), 4)
    for (dx, dy, bright) in A["dots"]:
        canvas.set_at((int(fcx) + dx, FY + dy), (255, 214, 100) if bright else (190, 110, 20))

    # rumput bergoyang
    for (x, h, p, col) in A["blades"]:
        s = int(round(math.sin(t * 1.8 + p + x / 9.0) * 1.2))
        pygame.draw.line(canvas, col, (x, GY), (x + s, GY - h))

    # kelopak jatuh & yang sudah di tanah: digambar SETELAH rumput (di depan rumput)
    for rank, k in enumerate(ORDER):
        tp = T0 + rank * STEP
        if t < tp:
            continue
        a = PETAL_ANG[k]
        lx, ly, la = landing_spot(k)
        u = t - tp
        if u < FALL_T:
            p = u / FALL_T
            sx, sy = fcx + 13 * math.cos(a), FY + 13 * math.sin(a)
            x = lerp(sx, lx, p) + math.sin(p * math.pi * 3 + k) * 9 * (1 - p)
            y = lerp(sy, ly, p ** 1.3)
            ang = lerp(-math.degrees(a), la + 360 * (1 if k % 2 else -1), p)
            blit_rot(canvas, A["petal_s"], x, y, ang)
        else:
            blit_rot(canvas, A["petal_s"], lx, ly, la)

    # hati naik setelah kelopak terakhir
    t_h = T0 + (NP - 1) * STEP + 0.4
    if t > t_h:
        for k in range(7):
            ph = ((t - t_h) * 0.55 + k * 0.15) % 1.2
            hx = fcx + math.sin(ph * 5 + k * 1.7) * (10 + k * 2) + (k - 3) * 4
            hy = FY - ph * 60
            al = max(0, min(255, int(255 * (1.2 - ph) / 0.5)))
            draw_heart(canvas, hx, hy, al)

    draw_cat(canvas, t)

    # tulisan
    picked = sum(1 for r in range(NP) if t >= T0 + r * STEP)
    if t < T0 or picked >= NP:
        msg, col = "LOVES ME", (240, 125, 172)
    elif picked % 2 == 1:
        msg, col = "LOVES ME NOT", (150, 170, 255)
    else:
        msg, col = "LOVES ME", (236, 128, 176)
    ts = text_surface(A["font"], msg, col, (120, 40, 90))
    canvas.blit(ts, ((W - ts.get_width()) // 2, 14))


# ---------------------------------------------------------------- main
def make_assets():
    rnd = random.Random(3)
    stars = [(rnd.randint(0, W - 1), rnd.randint(0, 165), rnd.random() * 6) for _ in range(55)]
    blades = []
    for x in range(W):
        h = rnd.randint(2, 6)
        p = rnd.random() * 6.28
        col = (44 + (x * 7) % 30, 150 + (x * 13) % 40 - 10, 56)
        blades.append((x, h, p, col))
    r2 = random.Random(5)
    dots = [(r2.randint(-6, 6), r2.randint(-6, 6), r2.random() > 0.4) for _ in range(16)]
    petal = make_petal((214, 234, 252), (150, 185, 230))
    petal_s = pygame.transform.scale(petal, (35, 35))     # kelopak jatuh sedikit lebih kecil
    try:
        font = pygame.font.SysFont("consolas,couriernew,dejavusansmono,monospace", 17, bold=True)
    except Exception:
        font = pygame.font.Font(None, 22)
    return {"bg": build_background(), "stars": stars, "blades": blades, "dots": dots,
            "petal": petal, "petal_s": petal_s, "font": font}


def main():
    pygame.init()
    screen = pygame.display.set_mode((W * SCALE, H * SCALE))
    pygame.display.set_caption("Loves me, loves me not")
    clock = pygame.time.Clock()
    canvas = pygame.Surface((W, H))
    A = make_assets()
    start = pygame.time.get_ticks()
    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                running = False
        t = ((pygame.time.get_ticks() - start) / 1000.0) % LOOP
        render(canvas, t, A)
        pygame.transform.scale(canvas, (W * SCALE, H * SCALE), screen)
        pygame.display.flip()
        clock.tick(FPS)
    pygame.quit()


if __name__ == "__main__":
    main()
