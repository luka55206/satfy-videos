"""Conform 9:16 Shorts into 16:9 compilation segments (our own clips only).

Each Short sits centred at full height over a blurred, dimmed copy of itself, with designed side panels:
left = slot number + title, right = "THE MATH" (one line that explains it). Every segment gets identical specs
(16:9, 60 fps, h264 yuv420p, AAC 48k stereo) so tools/build_compilation.py can stream-copy concat them.

  python tools/comp_916.py --list <comp.json> --outdir <folder> [--preview]
comp.json: [{"src": "...9x16.mp4", "name": "perfect_tree", "title": "...", "math": "..."}, ...]
--preview → 960x540 crf 20 (review); default → 3840x2160 crf 14.
"""
import json
import subprocess
import sys
from pathlib import Path

import cairo

GOLD = (1.0, 0.82, 0.40)


def _arg(flag, default=None):
    a = sys.argv
    return a[a.index(flag) + 1] if flag in a else default


def wrap(ctx, text, maxw):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if ctx.text_extents(t).x_advance <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def panel_png(path, W, H, slot, title, math_line):
    s = W / 1920
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    c.scale(s, s)
    fo = cairo.FontOptions()
    fo.set_antialias(cairo.ANTIALIAS_GRAY)                   # no coloured sub-pixel fringes
    c.set_font_options(fo)
    side = (1920 - 1080 * 9 / 16) / 2                       # width of each side zone (logical)
    for x0 in (0, 1920 - side):                              # designed backdrop (opaque): navy gradient + faint grid
        c.save()
        c.rectangle(x0, 0, side, 1080)
        c.clip()
        g = cairo.RadialGradient(x0 + side / 2, 470, 0, x0 + side / 2, 470, 760)
        g.add_color_stop_rgb(0, 0.09, 0.08, 0.17)
        g.add_color_stop_rgb(1, 0.02, 0.02, 0.05)
        c.set_source(g)
        c.paint()
        c.set_source_rgba(0.6, 0.65, 0.95, 0.07)
        c.set_line_width(1)
        for gx in range(int(x0) - int(x0) % 60, int(x0 + side) + 60, 60):
            c.move_to(gx, 0)
            c.line_to(gx, 1080)
        for gy in range(0, 1081, 60):
            c.move_to(x0, gy)
            c.line_to(x0 + side, gy)
        c.stroke()
        edge = x0 + side if x0 == 0 else x0                  # soft shadow where the Short meets the panel
        sh = cairo.LinearGradient(edge - 40, 0, edge + 40, 0)
        sh.add_color_stop_rgba(0, 0, 0, 0, 0.0 if x0 == 0 else 0.6)
        sh.add_color_stop_rgba(1, 0, 0, 0, 0.6 if x0 == 0 else 0.0)
        c.rectangle(edge - 40, 0, 80, 1080)
        c.set_source(sh)
        c.fill()
        c.restore()
    gl = cairo.RadialGradient(side / 2, 390, 0, side / 2, 390, 230)
    gl.add_color_stop_rgba(0, 1.0, 0.75, 0.3, 0.22)
    gl.add_color_stop_rgba(1, 1.0, 0.75, 0.3, 0.0)
    c.rectangle(0, 0, side, 1080)
    c.set_source(gl)
    c.fill()

    def text(t, x, y, size, col, bold=True, center=True, maxw=None):
        c.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
        c.set_font_size(size)
        lines = wrap(c, t, maxw) if maxw else [t]
        for i, ln in enumerate(lines):
            e = c.text_extents(ln)
            xx = x - e.width / 2 - e.x_bearing if center else x
            yy = y + i * size * 1.22
            c.set_source_rgba(0, 0, 0, 0.7)
            c.move_to(xx + 3, yy + 3)
            c.show_text(ln)
            c.set_source_rgb(*col)
            c.move_to(xx, yy)
            c.show_text(ln)
        return len(lines)

    lx = side / 2
    text(f"#{slot}" if isinstance(slot, int) else str(slot), lx, 430, 130 if isinstance(slot, int) else 96, GOLD)
    text(title, lx, 540, 46, (0.97, 0.97, 1.0), maxw=side * 0.84)
    rx = 1920 - side / 2
    text("THE MATH", rx, 440, 30, GOLD)
    text(math_line, rx, 510, 40, (0.92, 0.92, 0.97), bold=False, maxw=side * 0.84)
    surf.write_to_png(str(path))


def conform(src, panel, out, W, H, crf):
    fh = H
    fw = int(round(H * 9 / 16)) // 2 * 2
    fc = (f"[0:v]fps=60,split=2[a][b];"
          f"[a]scale={W}:{W * 16 // 9},crop={W}:{H},boxblur=20:2,eq=brightness=-0.18:saturation=0.8[bg];"
          f"[b]scale={fw}:{fh}[fg];"
          f"[bg][fg]overlay=(W-w)/2:0[v1];[v1][1:v]overlay=0:0,format=yuv420p[v]")
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(src), "-i", str(panel),
                    "-filter_complex", fc, "-map", "[v]", "-map", "0:a:0", "-r", "60", "-fps_mode", "cfr",
                    "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "384k", "-ar", "48000", "-ac", "2", str(out)], check=True)


def main():
    items = json.loads(Path(_arg("--list")).read_text(encoding="utf-8"))
    outdir = Path(_arg("--outdir"))
    outdir.mkdir(parents=True, exist_ok=True)
    prev = "--preview" in sys.argv
    W, H, crf = (960, 540, 20) if prev else (3840, 2160, 14)
    for i, it in enumerate(items, 1):
        panel = outdir / f"_panel_{i:02d}.png"
        panel_png(panel, W, H, it.get("label", i), it["title"], it["math"])
        out = outdir / f"{i:02d}_{it['name']}_16x9.mp4"
        conform(it["src"], panel, out, W, H, crf)
        panel.unlink()
        print(f"{i:02d} {it['name']}")


if __name__ == "__main__":
    main()
