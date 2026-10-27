"""The channel look and video I/O, defined once.

Every scene draws through Canvas and writes through VideoWriter so the whole
channel shares one visual identity and one encode recipe.

Conventions:
- World/canvas coordinates are ALWAYS full-res logical pixels (1080x1920 for
  9:16, 1920x1080 for 16:9). Fast mode renders at reduced scale via ctx.scale,
  so scene code never changes.
- cairo FORMAT_ARGB32 on little-endian Windows is BGRA in memory -> ffmpeg
  gets `-pix_fmt bgra`. Colors here are (r, g, b) floats 0..1.
- Determinism: no wall clock, no random calls in this module.
"""
import contextlib
import math
import os
import subprocess
from pathlib import Path

import cairo

FPS = 60
OUT_DIR = Path(__file__).resolve().parent.parent / "output"

# Neon-on-black channel palette (avoid immediate repeats when cycling).
PALETTE = [
    (0.00, 0.90, 1.00),  # cyan
    (1.00, 0.07, 0.47),  # hot pink
    (0.55, 1.00, 0.10),  # lime
    (1.00, 0.65, 0.00),  # orange
    (0.55, 0.25, 1.00),  # violet
    (1.00, 0.90, 0.10),  # yellow
    (0.10, 0.45, 1.00),  # royal blue
    (1.00, 0.20, 0.20),  # red
    (0.10, 1.00, 0.60),  # spring green
    (1.00, 0.30, 0.85),  # magenta
]

WHITE = (1.0, 1.0, 1.0)
BLACK = (0.0, 0.0, 0.0)

from lib.channel import WATERMARK  # noqa: E402


CAP_SIZE_F = 0.036   # historical caption size; see Canvas.caption


def is_fast() -> bool:
    return os.environ.get("NF_FAST", "") == "1"


def render_scale() -> float:
    """Output scale over the logical canvas size (logical stays 1080x1920 /
    1920x1080 so all layout/font math is resolution-independent).

    Default 2.0 => 4K delivery (2160x3840 / 3840x2160) — the channel renders
    4K for every video (Luka, 2026-07-04). Fast mode = 0.5 quick preview.
    Override with NF_SCALE (e.g. "1.0" for Full HD)."""
    if is_fast():
        return 0.5
    return float(os.environ.get("NF_SCALE", "2.0"))


_IMAGE_CACHE: dict = {}


def load_image(path):
    """Load any image file as a cairo surface, CACHED (a render loop asks for
    the same one thousands of times). Non-PNG goes through PIL in memory."""
    key = str(path)
    if key not in _IMAGE_CACHE:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"image not found: {p}")
        if p.suffix.lower() == ".png":
            _IMAGE_CACHE[key] = cairo.ImageSurface.create_from_png(str(p))
        else:
            from io import BytesIO
            from PIL import Image
            buf = BytesIO()
            Image.open(p).convert("RGBA").save(buf, format="PNG")
            buf.seek(0)
            _IMAGE_CACHE[key] = cairo.ImageSurface.create_from_png(buf)
    return _IMAGE_CACHE[key]


def hsv(h: float, s: float = 1.0, v: float = 1.0):
    """h in [0,1) -> (r,g,b). For continuous hue-cycling scenes."""
    i = int(h * 6.0) % 6
    f = h * 6.0 - int(h * 6.0)
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    return [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)][i]


class Canvas:
    """cairo surface + channel-look draw helpers at logical size w x h."""

    def __init__(self, w: int, h: int, scale: float = 1.0):
        self.w, self.h = w, h
        self.scale = scale
        self.pw, self.ph = int(w * scale) // 2 * 2, int(h * scale) // 2 * 2
        self.surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.pw, self.ph)
        self.ctx = cairo.Context(self.surf)
        self.ctx.scale(self.pw / w, self.ph / h)
        self.clear(BLACK)

    # --- frame ops ---------------------------------------------------------
    def clear(self, color=BLACK):
        self.ctx.set_source_rgb(*color)
        self.ctx.paint()

    def fade(self, alpha: float, color=BLACK):
        """Translucent wash for trail effects (draw instead of clear)."""
        self.ctx.set_source_rgba(*color, alpha)
        self.ctx.rectangle(0, 0, self.w, self.h)
        self.ctx.fill()

    def data(self) -> memoryview:
        self.surf.flush()
        return self.surf.get_data()

    # --- primitives --------------------------------------------------------
    def circle(self, x, y, r, color, alpha=1.0):
        self.ctx.set_source_rgba(*color, alpha)
        self.ctx.new_sub_path()
        self.ctx.arc(x, y, max(r, 0.1), 0, 2 * math.pi)
        self.ctx.fill()

    def ring(self, x, y, r, color, width=10.0, alpha=1.0):
        self.ctx.set_source_rgba(*color, alpha)
        self.ctx.set_line_width(width)
        self.ctx.new_sub_path()
        self.ctx.arc(x, y, max(r, 0.1), 0, 2 * math.pi)
        self.ctx.stroke()

    def arc_seg(self, x, y, r, a0, a1, color, width, alpha=1.0):
        """One glass segment (thick arc from a0 to a1). Used for the ring that
        is actively shattering so gaps open where segments break away."""
        self.ctx.set_source_rgba(*color, alpha)
        self.ctx.set_line_width(width)
        self.ctx.set_line_cap(cairo.LINE_CAP_BUTT)
        self.ctx.new_sub_path()
        self.ctx.arc(x, y, max(r, 0.1), a0, a1)
        self.ctx.stroke()

    def core(self, x, y, r, color, alpha=1.0, glow=0.5):
        """Center hub the ball breaks through to (glow + white-rimmed disc)."""
        self.glow(x, y, r, color, strength=glow, reach=2.4)
        self.circle_outlined(x, y, r, color, rim=WHITE, rim_w=2.5, alpha=alpha)

    def circle_outlined(self, x, y, r, fill, rim=WHITE, rim_w=2.0, alpha=1.0):
        self.circle(x, y, r, fill, alpha)
        if rim_w > 0:
            self.ctx.set_source_rgba(*rim, alpha)
            self.ctx.set_line_width(rim_w)
            self.ctx.new_sub_path()
            self.ctx.arc(x, y, max(r, 0.1), 0, 2 * math.pi)
            self.ctx.stroke()

    def ngon_outline(self, x, y, circR, n, theta, color, width=2.0, alpha=1.0):
        """Regular-n-gon analog of ring()/square_outline() — a stroked outline
        with mitered corners (a polygon arena wall). circR is the CIRCUMradius;
        vertex k sits at angle theta + 2*pi*k/n (+y down), matching
        analytic.regular_polygon so the wall drawn is the wall collided with."""
        self.ctx.set_source_rgba(*color, alpha)
        self.ctx.set_line_width(width)
        self.ctx.set_line_join(cairo.LINE_JOIN_MITER)
        R = max(circR, 0.1)
        for k in range(n):
            a = theta + 2.0 * math.pi * k / n
            px, py = x + R * math.cos(a), y + R * math.sin(a)
            if k == 0:
                self.ctx.move_to(px, py)
            else:
                self.ctx.line_to(px, py)
        self.ctx.close_path()
        self.ctx.stroke()

    def square_outline(self, x, y, half, color, width=2.0, alpha=1.0):
        """Square analog of ring() — a stroked square outline (ghost rims,
        background hints, the outer wall)."""
        self.ctx.set_source_rgba(*color, alpha)
        self.ctx.set_line_width(width)
        self.ctx.rectangle(x - half, y - half, 2 * max(half, 0.1), 2 * max(half, 0.1))
        self.ctx.stroke()

    def square_filled(self, x, y, half, color, alpha=1.0):
        self.ctx.set_source_rgba(*color, alpha)
        self.ctx.rectangle(x - half, y - half, 2 * max(half, 0.1), 2 * max(half, 0.1))
        self.ctx.fill()

    def square_outlined(self, x, y, half, fill, rim=WHITE, rim_w=2.0, alpha=1.0):
        """Square analog of circle_outlined()."""
        self.square_filled(x, y, half, fill, alpha)
        if rim_w > 0:
            self.ctx.set_source_rgba(*rim, alpha)
            self.ctx.set_line_width(rim_w)
            self.ctx.rectangle(x - half, y - half, 2 * max(half, 0.1), 2 * max(half, 0.1))
            self.ctx.stroke()

    def rect(self, x0, y0, x1, y1, color, alpha=1.0):
        """Filled axis-aligned rectangle from arbitrary corners (bricks) —
        the non-centered generalization of square_filled()."""
        self.ctx.set_source_rgba(*color, alpha)
        self.ctx.rectangle(x0, y0, x1 - x0, y1 - y0)
        self.ctx.fill()

    @contextlib.contextmanager
    def clipped_circle(self, x, y, r):
        """Restrict drawing to inside a circle for the duration of the block.

        For debris that must stay INSIDE a closed arena: a shatter burst whose
        splinters cross the rim breaks the containment the whole scene rests on.
        """
        self.ctx.save()
        self.ctx.new_sub_path()
        self.ctx.arc(x, y, max(r, 0.1), 0, 2 * math.pi)
        self.ctx.clip()
        try:
            yield
        finally:
            self.ctx.restore()

    def poly(self, pts, fill, rim=None, rim_w=0.0, alpha=1.0):
        """Filled closed polygon from [(x,y), ...], optional stroked rim.

        The general primitive circle/square/rect don't cover — used for the
        spike tooth on spike_gate's rim. Rim is stroked after the fill so a
        white outline reads over a colored body.
        """
        if len(pts) < 3:
            return
        self.ctx.move_to(*pts[0])
        for p in pts[1:]:
            self.ctx.line_to(*p)
        self.ctx.close_path()
        self.ctx.set_source_rgba(*fill, alpha)
        if rim is not None and rim_w > 0:
            self.ctx.fill_preserve()
            self.ctx.set_source_rgba(*rim, alpha)
            self.ctx.set_line_width(rim_w)
            self.ctx.stroke()
        else:
            self.ctx.fill()

    def glass_rect(self, x0, y0, x1, y1, color, alpha=0.55, rim_w=2.0,
                   rim_alpha=0.85, sheen=0.35):
        """A pane of colored GLASS: a translucent fill, a bright lit edge, and
        a diagonal top-left sheen streak — so it reads as lit glass, not a
        solid tile. rim/sheen are lightened tints of `color` (pushed toward
        white) = the glass catching light. Used for the break_grid glass grid."""
        light = tuple(min(1.0, c * 0.35 + 0.65) for c in color)   # bright tint
        self.ctx.set_source_rgba(*color, alpha)
        self.ctx.rectangle(x0, y0, x1 - x0, y1 - y0)
        self.ctx.fill()
        if sheen > 0:                                             # corner glint
            self.ctx.set_source_rgba(*light, sheen)
            self.ctx.rectangle(x0, y0, (x1 - x0) * 0.5, (y1 - y0) * 0.5)
            self.ctx.fill()
        if rim_w > 0:                                             # lit edge
            self.ctx.set_source_rgba(*light, rim_alpha)
            self.ctx.set_line_width(rim_w)
            self.ctx.rectangle(x0 + rim_w * 0.5, y0 + rim_w * 0.5,
                               (x1 - x0) - rim_w, (y1 - y0) - rim_w)
            self.ctx.stroke()

    def square_core(self, x, y, half, color, alpha=1.0, glow=0.5):
        """Square analog of core() — the halo stays a circular glow (a soft
        radial light halo reads fine around a square hub) but the hub itself
        is a filled, white-rimmed square."""
        self.glow(x, y, half, color, strength=glow, reach=2.4)
        self.square_outlined(x, y, half, color, rim=WHITE, rim_w=2.5, alpha=alpha)

    def line(self, x0, y0, x1, y1, color, width=2.0, alpha=1.0):
        self.ctx.set_source_rgba(*color, alpha)
        self.ctx.set_line_width(width)
        self.ctx.move_to(x0, y0)
        self.ctx.line_to(x1, y1)
        self.ctx.stroke()

    def lines(self, segments, color, width=2.0, alpha=1.0, cap=None):
        """Many segments [(x0,y0,x1,y1), ...] in one stroke call.

        ``cap='round'`` strokes each segment as a CAPSULE. Needed when the
        segments chain along a curve (butt caps leave a visible notch at every
        joint on a tight coil) and when a segment IS a physical capsule --
        spiral_core's destructible wall collides against exactly this shape,
        so drawing it with butt caps would put the pixels and the collider a
        half-thickness apart at every brick end.
        """
        if not segments:
            return
        if cap == "round":
            self.ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        self.ctx.set_source_rgba(*color, alpha)
        self.ctx.set_line_width(width)
        for x0, y0, x1, y1 in segments:
            self.ctx.move_to(x0, y0)
            self.ctx.line_to(x1, y1)
        self.ctx.stroke()
        if cap == "round":
            self.ctx.set_line_cap(cairo.LINE_CAP_BUTT)

    def polylines(self, paths, color, width=2.0, alpha=1.0):
        """Many CONNECTED point-chains [[(x, y), ...], ...] in one stroke call.

        The chained cousin of lines(): a chain of capsules drawn with lines()
        overlaps itself at every shared endpoint, so at alpha < 1 each joint
        composites twice and the ribbon reads as beads. Stroking the chain as
        ONE path with round joins+caps draws the union exactly once, giving a
        single continuous line of constant weight -- while still covering
        precisely the same pixels as the capsule chain it collides against
        (round join == the cap disc at the joint).

        One stroke() for the whole batch, so the union is composited once
        across every chain too; keep same-alpha work in a single call.
        """
        paths = [p for p in paths if len(p) >= 2]
        if not paths:
            return
        self.ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        self.ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        self.ctx.set_source_rgba(*color, alpha)
        self.ctx.set_line_width(width)
        for pts in paths:
            self.ctx.move_to(*pts[0])
            for pt in pts[1:]:
                self.ctx.line_to(*pt)
        self.ctx.stroke()
        self.ctx.set_line_cap(cairo.LINE_CAP_BUTT)
        self.ctx.set_line_join(cairo.LINE_JOIN_MITER)

    def polylines_vgrad(self, paths, y0, y1, colors, width=2.0, alpha=1.0):
        """polylines() whose colour is a VERTICAL GRADIENT: `colors` spread
        evenly from y0 to y1 (two entries = a simple ramp, more = a spectrum).

        A cairo LinearGradient as the stroke source, so the whole chain is one
        stroke() and the ribbon keeps polylines()' guarantee of compositing
        every pixel exactly once. Splitting the path into per-colour segments
        instead re-composites each shared endpoint and the line reads as beads
        (the solved_bounce lesson) -- the gradient source avoids that entirely,
        and is smooth rather than banded into steps.

        Colour by HEIGHT is the useful case: it makes a vertical position
        readable as a hue without adding any time dependence, so it is safe in
        a wrap loop where a hue that drifts with t is not.
        """
        paths = [p for p in paths if len(p) >= 2]
        if not paths or not colors:
            return
        g = cairo.LinearGradient(0.0, y0, 0.0, y1)
        n = len(colors)
        for i, c in enumerate(colors):
            g.add_color_stop_rgba(i / (n - 1) if n > 1 else 0.0, *c, alpha)
        self.ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        self.ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        self.ctx.set_source(g)
        self.ctx.set_line_width(width)
        for pts in paths:
            self.ctx.move_to(*pts[0])
            for pt in pts[1:]:
                self.ctx.line_to(*pt)
        self.ctx.stroke()
        self.ctx.set_line_cap(cairo.LINE_CAP_BUTT)
        self.ctx.set_line_join(cairo.LINE_JOIN_MITER)

    def glow(self, x, y, r, color, strength=0.6, reach=2.6):
        """Additive-looking halo via radial gradient (cairo has no blur)."""
        g = cairo.RadialGradient(x, y, r * 0.6, x, y, r * reach)
        g.add_color_stop_rgba(0.0, *color, strength)
        g.add_color_stop_rgba(1.0, *color, 0.0)
        self.ctx.set_source(g)
        self.ctx.new_sub_path()
        self.ctx.arc(x, y, r * reach, 0, 2 * math.pi)
        self.ctx.fill()

    # --- text / UI ---------------------------------------------------------
    def _font(self, size, bold=True):
        self.ctx.select_font_face(
            "Arial",
            cairo.FONT_SLANT_NORMAL,
            cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL,
        )
        self.ctx.set_font_size(size)

    def text_centered(self, s, y, size=64, color=WHITE, alpha=1.0, bold=True,
                      max_w=None, cx=None):
        """Text centered on cx (default: canvas center) with a soft shadow.

        max_w (default 92% of canvas width) shrinks the font to fit.
        """
        self._font(size, bold)
        ext = self.ctx.text_extents(s)
        limit = max_w if max_w is not None else self.w * 0.92
        if ext.width > limit:
            self._font(size * limit / ext.width, bold)
            ext = self.ctx.text_extents(s)
        center = cx if cx is not None else self.w / 2
        x = center - ext.width / 2 - ext.x_bearing
        self.ctx.set_source_rgba(0, 0, 0, 0.45 * alpha)
        self.ctx.move_to(x + 3, y + 3)
        self.ctx.show_text(s)
        self.ctx.set_source_rgba(*color, alpha)
        self.ctx.move_to(x, y)
        self.ctx.show_text(s)

    @staticmethod
    def _span_colors(span_color):
        """Normalise span_color to a LIST of (r,g,b), or None.

        One (r,g,b) -> a one-entry list (every span that colour, the original
        behaviour). A sequence of them stays a list and is consumed in span
        order by text_block."""
        if span_color is None:
            return None
        if isinstance(span_color[0], (int, float)):
            return [tuple(span_color)]
        return [tuple(c) for c in span_color]

    @staticmethod
    def _spans(s):
        """Split '...~word~...' into [(text, in_span)] segments. Text without
        '~' comes back as one plain segment."""
        parts = s.split("~")
        segs = [(t, bool(i % 2)) for i, t in enumerate(parts) if t != ""]
        return segs or [("", False)]

    def text_block(self, lines, y, size=64, color=WHITE, alpha=1.0, bold=True,
                   max_w=None, cx=None, line_gap=1.22, span_color=None,
                   span_scale=1.0):
        """Stacked centered lines from baseline y downward, all sharing one
        font size chosen so the widest line fits max_w. Soft shadow each line.

        ``~word~`` marks a SPAN drawn in ``span_color`` (the fire episode's
        blue WATER). With span_color None the markers are stripped and the
        draw path is the original single show_text — every existing caption
        (none contain '~') renders bit-identically.

        ``span_color`` is EITHER one (r,g,b) — every span that colour — OR a
        LIST of them, handed to the spans in ORDER OF APPEARANCE across the
        whole block and cycling when it runs out (turf elim4: color / ERASED /
        color -> yellow / red / yellow). One colour behaves exactly as
        before.

        ``span_scale`` draws the spans at that multiple of the base size, on
        the SAME baseline, so a caption can make one word BIGGER as well as
        coloured. Like ``span_color`` it is EITHER one number (every span) OR a
        LIST handed to the spans in ORDER OF APPEARANCE, cycling — so
        ``[1, 1, 1.35]`` enlarges only the THIRD span. It is measured into the
        shrink-to-fit, so a scaled-up span pushes the rest of the block DOWN in
        size rather than off the edge. All-1.0 takes the original code path
        exactly — every caption ever shipped renders bit-identically."""
        center = cx if cx is not None else self.w / 2
        limit = max_w if max_w is not None else self.w * 0.92
        span_cols = self._span_colors(span_color)
        si = 0
        segs_per = [self._spans(s) for s in lines]
        plain = ["".join(t for t, _ in segs) for segs in segs_per]
        scales = self._span_scales(span_scale)
        if any(v != 1.0 for v in scales) and any(sp for segs in segs_per
                                                 for _, sp in segs):
            return self._text_block_scaled(
                segs_per, y, size, color, alpha, bold, limit, center,
                line_gap, span_cols, scales)
        self._font(size, bold)
        widest = max(self.ctx.text_extents(s).width for s in plain)
        if widest > limit:
            size = size * limit / widest
            self._font(size, bold)
        for i, segs in enumerate(segs_per):
            s = plain[i]
            ext = self.ctx.text_extents(s)
            x = center - ext.width / 2 - ext.x_bearing
            ly = y + i * size * line_gap
            if span_color is None or not any(sp for _, sp in segs):
                self.ctx.set_source_rgba(0, 0, 0, 0.45 * alpha)
                self.ctx.move_to(x + 3, ly + 3)
                self.ctx.show_text(s)
                self.ctx.set_source_rgba(*color, alpha)
                self.ctx.move_to(x, ly)
                self.ctx.show_text(s)
                continue
            # segment path: advance left -> right, colouring the spans.
            # Centering uses the whole line's extents, so the text sits
            # exactly where the plain path would put it.
            sx = x
            for (t, in_span) in segs:
                self.ctx.set_source_rgba(0, 0, 0, 0.45 * alpha)
                self.ctx.move_to(sx + 3, ly + 3)
                self.ctx.show_text(t)
                if in_span:
                    col = span_cols[si % len(span_cols)]
                    si += 1
                else:
                    col = color
                self.ctx.set_source_rgba(*col, alpha)
                self.ctx.move_to(sx, ly)
                self.ctx.show_text(t)
                sx += self.ctx.text_extents(t).x_advance

    @staticmethod
    def _span_scales(span_scale):
        """1.4 -> [1.4]; [1.0, 1.35] -> itself. Handed to the spans in ORDER
        OF APPEARANCE and cycling, exactly like span_color."""
        if span_scale is None:
            return [1.0]
        if isinstance(span_scale, (int, float)):
            return [float(span_scale)]
        return [float(v) for v in span_scale] or [1.0]

    def _text_block_scaled(self, segs_per, y, size, color, alpha, bold, limit,
                           center, line_gap, span_cols, scales):
        """text_block's mixed-SIZE path (some span drawn at != 1.0).

        Widths are summed from per-segment x_advance at each segment's own font
        size — the plain path's single text_extents() cannot measure a line
        whose parts are different sizes. Spans share the baseline with the rest
        of the line, so a bigger word grows UPWARD; the line step stays keyed to
        the base size, which at the sizes a caption uses leaves the taller word
        clear of the line above (verified on the rendered frame).

        The per-span scale is resolved ONCE into `fs_per`, before measuring, so
        the width the shrink-to-fit sees and the width actually drawn cannot
        disagree — they walk the same list.
        """
        si = 0
        fs_per = []                       # size MULTIPLE per segment, in order
        for segs in segs_per:
            row = []
            for _t, in_span in segs:
                if in_span:
                    row.append(scales[si % len(scales)])
                    si += 1
                else:
                    row.append(1.0)
            fs_per.append(row)

        def line_w(i, sz):
            w = 0.0
            for (t, _sp), m in zip(segs_per[i], fs_per[i]):
                self._font(sz * m, bold)
                w += self.ctx.text_extents(t).x_advance
            return w

        widest = max(line_w(i, size) for i in range(len(segs_per)))
        if widest > limit:
            size = size * limit / widest
        si = 0
        for i, segs in enumerate(segs_per):
            sx = center - line_w(i, size) / 2.0
            ly = y + i * size * line_gap
            for (t, in_span), m in zip(segs, fs_per[i]):
                self._font(size * m, bold)
                self.ctx.set_source_rgba(0, 0, 0, 0.45 * alpha)
                self.ctx.move_to(sx + 3, ly + 3)
                self.ctx.show_text(t)
                if in_span:
                    col = span_cols[si % len(span_cols)]
                    si += 1
                else:
                    col = color
                self.ctx.set_source_rgba(*col, alpha)
                self.ctx.move_to(sx, ly)
                self.ctx.show_text(t)
                sx += self.ctx.text_extents(t).x_advance

    def caption(self, s, alpha=1.0, layout=None, size_f=CAP_SIZE_F,
                span_color=None, span_scale=1.0, line_gap=1.22):
        """Hook caption at the layout's anchor. '\\n' splits into stacked lines.
        ``~word~`` + ``span_color`` colours a word (see text_block).

        ``size_f`` is the font size as a fraction of canvas height. The 0.036
        default is the historical channel size, so every scene that does not
        pass it renders bit-identically.

        It is an ASKED size: `text_block` shrinks to fit ``cap_maxw``, and a
        full-width caption is usually ALREADY shrink-limited — survivor's asked
        69.1px rendered at 59.2px, so 0.036 -> 0.032 changed nothing at all.
        Consequence worth knowing: shortening the TEXT of such a caption makes
        it BIGGER, not smaller. Only lowering ``size_f`` past the fit point
        makes it smaller.

        ``span_scale`` draws ~spans~ at that multiple of the size (see
        text_block) — the way to make ONE word bigger as well as coloured.

        ``line_gap`` is the baseline step as a multiple of the BASE size; the
        1.22 default is the channel's, so every existing caption renders
        bit-identically. Raise it when a whole LINE is scaled up — the step is
        keyed to the base size, so a line at 1.7x grows UPWARD into the line
        above it (hydro_press shr23 needs 1.75 to clear line 1's descenders).

        A clip that changes this, ``size_f``, ``span_scale`` or ``line_gap``
        must pass the SAME value to `add_caption.py` and `megamix_intro.py`, or
        the 16:9 intro's title will not land pixel-matched on the baked caption
        it hands off to.
        """
        lines = s.split("\n")
        if layout is None:
            self.text_block(lines, self.h * 0.14, size=self.h * size_f,
                            alpha=alpha, span_color=span_color,
                            span_scale=span_scale, line_gap=line_gap)
        else:
            self.text_block(lines, layout.cap_y, size=self.h * size_f,
                            alpha=alpha, cx=layout.cap_x,
                            max_w=layout.cap_maxw, span_color=span_color,
                            span_scale=span_scale, line_gap=line_gap)

    def counter(self, s, alpha=1.0, layout=None, size_f=0.024):
        """Live number at the layout's counter anchor.

        ``size_f`` is the font size as a fraction of canvas height; the 0.024
        default is the historical channel size (every pre-2026-07-29 scene
        renders bit-identically without passing it). Newer scenes pass a
        BIGGER value — competitor evidence (research/channel-analysis.md, the
        CodeCraftedPhysics telemetry-HUD lesson) is that feed legibility comes
        from big readable numbers, and a percent-to-goal readout is only a hook
        if it can be read at thumbnail size."""
        if layout is None:
            self.text_centered(s, self.h * 0.87, size=self.h * size_f, alpha=alpha)
        else:
            self.text_centered(s, layout.cnt_y, size=self.h * size_f, alpha=alpha,
                               cx=layout.cnt_x, max_w=layout.cnt_maxw)

    def goal_bar(self, frac, layout, color, alpha=1.0, width_f=0.62,
                 height_f=0.0075, dy_f=0.026):
        """Game-UI progress bar under the counter: a dim track with a bright
        theme-colored fill showing ``frac`` (0..1) of the way to the scene's
        stated destination.

        The channel's "state a DESTINATION, not just a rule" lesson wants a
        number visibly CONVERGING to the promised end state; the bar is the
        same information as a shape, readable in the half-second a scrolling
        viewer gives a tile. Geometry comes from the layout's counter anchor
        (never hardcoded pixels), so it lands in the bottom band in 9:16 and in
        the right side panel in 16:9. Rounded caps, so an empty bar still reads
        as a track rather than a hairline."""
        frac = 0.0 if frac < 0.0 else (1.0 if frac > 1.0 else frac)
        w = min(layout.cnt_maxw, self.w * width_f)
        h = max(self.h * height_f, 3.0)
        x0 = layout.cnt_x - w / 2.0
        y = layout.cnt_y + self.h * dy_f
        self.ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        self.ctx.set_line_width(h)
        self.ctx.set_source_rgba(1, 1, 1, 0.18 * alpha)
        self.ctx.move_to(x0 + h / 2, y)
        self.ctx.line_to(x0 + w - h / 2, y)
        self.ctx.stroke()
        if frac > 0.0:
            span = (w - h) * frac
            self.ctx.set_source_rgba(*color, 0.95 * alpha)
            self.ctx.move_to(x0 + h / 2, y)
            self.ctx.line_to(x0 + h / 2 + span, y)
            self.ctx.stroke()
        self.ctx.set_line_cap(cairo.LINE_CAP_BUTT)

    def versus_bar(self, frac_a, layout, color_a, color_b, alpha=1.0,
                   width_f=0.62, height_f=0.011, dy_f=0.026):
        """Two-colour TUG-OF-WAR bar: A grows from the left, B from the right,
        meeting at ``frac_a``.

        Distinct from goal_bar, and the distinction is the whole point: goal_bar
        shows progress toward ONE destination, so an empty track means "not
        there yet". Here the bar is ALWAYS full and only the boundary moves —
        which is what a two-sided contest looks like. Using goal_bar for a
        versus scene reads as a loading bar instead of a fight (Luka,
        2026-07-31). Same construction turf uses for its territory split."""
        frac_a = 0.0 if frac_a < 0.0 else (1.0 if frac_a > 1.0 else frac_a)
        w = min(layout.cnt_maxw, self.w * width_f)
        h = max(self.h * height_f, 4.0)
        x0 = layout.cnt_x - w / 2.0
        y = layout.cnt_y + self.h * dy_f
        split = x0 + w * frac_a
        self.ctx.set_source_rgba(*color_a, alpha)
        self.ctx.rectangle(x0, y - h / 2, max(split - x0, 0.0), h)
        self.ctx.fill()
        self.ctx.set_source_rgba(*color_b, alpha)
        self.ctx.rectangle(split, y - h / 2, max(x0 + w - split, 0.0), h)
        self.ctx.fill()

    def image(self, surface, cx, cy, w, alpha=1.0):
        """Draw a loaded image surface centered on (cx, cy), scaled to width w.

        FILTER_BEST because these are almost always UPSCALES — a UI screenshot
        is a few hundred px wide and the 4K canvas is 2160.
        """
        sw, sh = surface.get_width(), surface.get_height()
        if sw <= 0 or sh <= 0:
            return 0.0
        k = w / sw
        h = sh * k
        self.ctx.save()
        self.ctx.translate(cx - w / 2, cy - h / 2)
        self.ctx.scale(k, k)
        self.ctx.set_source_surface(surface, 0, 0)
        self.ctx.get_source().set_filter(cairo.FILTER_BEST)
        self.ctx.paint_with_alpha(alpha)
        self.ctx.restore()
        return h

    def comment_card(self, cx, cy, w, handle, text, age="3 days ago",
                     likes=1, alpha=1.0, hearted=True):
        """A YouTube-comment card — for "reply to a viewer's comment" openers.

        DRAWN, not a pasted screenshot, on purpose: a real screenshot is ~350px
        wide and would be a 5x upscale to fill a 2160px-wide frame, i.e. mush at
        4K. This renders vector-crisp at any scale. Everything is laid out in
        units of `w` so it survives both orientations.

        Only reproduces a comment the channel actually received — the handle and
        text are passed in by the scene, never invented here.
        """
        pad = w * 0.055
        av = w * 0.105                       # avatar diameter
        body = w * 0.052                     # comment font size
        meta = w * 0.040                     # handle / "3 days ago" size
        h = pad * 2 + av * 2.15
        x0, y0 = cx - w / 2, cy - h / 2
        r = w * 0.028                        # corner radius

        self.ctx.save()
        self.ctx.new_sub_path()              # rounded rect
        self.ctx.arc(x0 + w - r, y0 + r, r, -math.pi / 2, 0)
        self.ctx.arc(x0 + w - r, y0 + h - r, r, 0, math.pi / 2)
        self.ctx.arc(x0 + r, y0 + h - r, r, math.pi / 2, math.pi)
        self.ctx.arc(x0 + r, y0 + r, r, math.pi, 1.5 * math.pi)
        self.ctx.close_path()
        self.ctx.set_source_rgba(0.97, 0.97, 0.97, alpha)
        self.ctx.fill()

        ax, ay = x0 + pad + av / 2, y0 + pad + av / 2
        self.ctx.set_source_rgba(0.25, 0.65, 0.35, alpha)   # avatar
        self.ctx.arc(ax, ay, av / 2, 0, 2 * math.pi)
        self.ctx.fill()
        self._font(av * 0.62, bold=True)
        initial = handle.lstrip("@")[:1].upper()
        ext = self.ctx.text_extents(initial)
        self.ctx.set_source_rgba(1, 1, 1, alpha)
        self.ctx.move_to(ax - ext.width / 2 - ext.x_bearing,
                         ay - ext.height / 2 - ext.y_bearing)
        self.ctx.show_text(initial)

        tx = x0 + pad + av + w * 0.035
        self._font(meta, bold=True)
        self.ctx.set_source_rgba(0.07, 0.07, 0.07, alpha)
        self.ctx.move_to(tx, y0 + pad + av * 0.45)
        self.ctx.show_text(handle)
        hw = self.ctx.text_extents(handle).x_advance
        self._font(meta, bold=False)
        self.ctx.set_source_rgba(0.40, 0.40, 0.40, alpha)
        self.ctx.move_to(tx + hw + w * 0.022, y0 + pad + av * 0.45)
        self.ctx.show_text(age)

        self._font(body, bold=False)
        self.ctx.set_source_rgba(0.05, 0.05, 0.05, alpha)
        self.ctx.move_to(tx, y0 + pad + av * 1.20)
        self.ctx.show_text(text)

        # action row: thumb up + count, thumb down, creator heart, Reply
        iy = y0 + pad + av * 1.85
        ic = w * 0.030
        self._thumb(tx + ic, iy, ic, alpha, up=True)
        self._font(meta * 0.92, bold=False)
        self.ctx.set_source_rgba(0.35, 0.35, 0.35, alpha)
        self.ctx.move_to(tx + ic * 2.2, iy + ic * 0.45)
        self.ctx.show_text(str(likes))
        self._thumb(tx + ic * 5.0, iy, ic, alpha, up=False)
        if hearted:
            self._heart(tx + ic * 8.0, iy, ic * 1.15, alpha)
        self._font(meta * 0.92, bold=True)
        self.ctx.set_source_rgba(0.35, 0.35, 0.35, alpha)
        self.ctx.move_to(tx + ic * 10.2, iy + ic * 0.45)
        self.ctx.show_text("Reply")
        self.ctx.restore()
        return h

    def _thumb(self, x, y, s, alpha, up=True):
        """Small thumbs-up/down glyph (outline, like YouTube's)."""
        self.ctx.save()
        self.ctx.translate(x, y)
        if not up:
            self.ctx.scale(1, -1)
        self.ctx.set_source_rgba(0.35, 0.35, 0.35, alpha)
        self.ctx.set_line_width(s * 0.16)
        self.ctx.rectangle(-s * 0.62, -s * 0.02, s * 0.36, s * 0.62)
        self.ctx.stroke()
        self.ctx.move_to(-s * 0.16, s * 0.60)
        self.ctx.line_to(-s * 0.16, s * 0.02)
        self.ctx.line_to(s * 0.16, -s * 0.62)
        self.ctx.line_to(s * 0.40, -s * 0.44)
        self.ctx.line_to(s * 0.30, s * 0.02)
        self.ctx.line_to(s * 0.62, s * 0.02)
        self.ctx.line_to(s * 0.44, s * 0.60)
        self.ctx.close_path()
        self.ctx.stroke()
        self.ctx.restore()

    def _heart(self, x, y, s, alpha):
        """Filled heart — the creator's ❤ badge on a comment."""
        self.ctx.save()
        self.ctx.translate(x, y + s * 0.05)
        self.ctx.set_source_rgba(0.90, 0.15, 0.30, alpha)
        self.ctx.move_to(0, s * 0.42)
        self.ctx.curve_to(-s * 0.75, -s * 0.10, -s * 0.36, -s * 0.62, 0, -s * 0.22)
        self.ctx.curve_to(s * 0.36, -s * 0.62, s * 0.75, -s * 0.10, 0, s * 0.42)
        self.ctx.close_path()
        self.ctx.fill()
        self.ctx.restore()

    def watermark(self, layout=None, color=WHITE, alpha=0.22):
        """Faint watermark below the arena center. Anchored to the arena's
        OWN position/radius (not a fixed fraction of canvas height) so it
        reliably clears a persistent center object (e.g. break_rings' core)
        in every orientation — 9:16 and 16:9 place the arena at very
        different heights relative to the canvas, so a single height
        fraction can't clear both (Luka's catch, 2026-07-05: still visibly
        cut through the core in 16:9 even after the earlier 9:16-only fix).

        ``color``/``alpha`` exist for light-field scenes (fill_circle
        --invert draws on a solid WHITE disc, where the default white text
        vanishes) — defaults are the channel look, don't change them."""
        if layout is not None:
            size = layout.wm_size
            y = layout.arena_cy + layout.arena_R * 0.32
        else:
            size = self.h * 0.016
            y = self.h * 0.56
        self.text_centered(WATERMARK, y, size=size, color=color, alpha=alpha,
                           bold=False)


class VideoWriter:
    """Pipes raw BGRA frames into ffmpeg -> H.264 yuv420p mp4."""

    def __init__(self, path, canvas: Canvas, fps: int = FPS, crf: int = None):
        # NF_CRF lets a caption-less BASE render be cut finer (e.g. 14) so that
        # tools/add_caption.py's second encode still lands at the usual crf 18.
        crf = int(os.environ.get("NF_CRF", 18)) if crf is None else crf
        self.path = str(path)
        self.canvas = canvas
        self.proc = subprocess.Popen(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
             "-f", "rawvideo", "-pix_fmt", "bgra",
             "-s", f"{canvas.pw}x{canvas.ph}", "-r", str(fps), "-i", "pipe:0",
             "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
             "-pix_fmt", "yuv420p", "-movflags", "+faststart", self.path],
            stdin=subprocess.PIPE,
        )

    def write_frame(self):
        self.proc.stdin.write(self.canvas.data())

    def close(self):
        self.proc.stdin.close()
        rc = self.proc.wait()
        if rc != 0:
            raise RuntimeError(f"ffmpeg exited {rc} for {self.path}")


def save_still(canvas: Canvas, path):
    canvas.surf.flush()
    canvas.surf.write_to_png(str(path))


def mux_audio(video_path, wav_path, out_path):
    """Attach mastered WAV to a rendered video without re-encoding it."""
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-i", str(video_path), "-i", str(wav_path),
         "-map", "0:v:0", "-map", "1:a:0",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "384k", "-shortest",
         str(out_path)],
        check=True,
    )
