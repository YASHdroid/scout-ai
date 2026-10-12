"use client";

import { useEffect, useRef } from "react";



const LEVELS = 12;
const BASE_RGB = [138, 160, 186] as const;
const GLOW_RGB = [56, 189, 248] as const;


const BLOBS = [
  { x: 0.74, y: 0.38, s: 1.0, a: 0.55 },
  { x: 0.16, y: 1.3, s: 0.9, a: 0.45 },
  { x: 0.84, y: 2.2, s: 1.0, a: 0.5 },
  { x: 0.28, y: 3.1, s: 0.9, a: 0.45 },
  { x: 0.76, y: 4.0, s: 1.0, a: 0.5 },
  { x: 0.2, y: 4.9, s: 0.9, a: 0.45 },
];

type LiveBlob = { cx: number; cy: number; inv: number; a: number; i: number };

export default function SignalField() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let w = 0;
    let h = 0;
    let spacing = 26;
    let cols = 0;
    let rows = 0;
    let heat = new Float32Array(0);
    let phase = new Float32Array(0);
    let raf = 0;
    let last = performance.now();
    const start = last;
    let prev: { x: number; y: number } | null = null;

    const styles = Array.from({ length: LEVELS }, (_, i) => {
      const k = i / (LEVELS - 1);
      const r = Math.round(BASE_RGB[0] + (GLOW_RGB[0] - BASE_RGB[0]) * k);
      const g = Math.round(BASE_RGB[1] + (GLOW_RGB[1] - BASE_RGB[1]) * k);
      const b = Math.round(BASE_RGB[2] + (GLOW_RGB[2] - BASE_RGB[2]) * k);
      const a = 0.13 + k * 0.72;
      return `rgba(${r},${g},${b},${a.toFixed(3)})`;
    });

    const resize = () => {
      w = window.innerWidth;
      h = window.innerHeight;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      spacing = w < 640 ? 20 : 26;
      cols = Math.ceil(w / spacing) + 1;
      rows = Math.ceil(h / spacing) + 1;
      heat = new Float32Array(cols * rows);
      phase = new Float32Array(cols * rows);
      for (let i = 0; i < phase.length; i++) phase[i] = Math.random() * Math.PI * 2;
    };

    // Add heat around a point; dots inside the radius light up.
    const stamp = (px: number, py: number) => {
      const R = w < 640 ? 80 : 120;
      const c0 = Math.max(0, Math.floor((px - R) / spacing));
      const c1 = Math.min(cols - 1, Math.ceil((px + R) / spacing));
      const r0 = Math.max(0, Math.floor((py - R) / spacing));
      const r1 = Math.min(rows - 1, Math.ceil((py + R) / spacing));
      for (let r = r0; r <= r1; r++) {
        const dy = r * spacing - py;
        for (let c = c0; c <= c1; c++) {
          const dx = c * spacing - px;
          const d = Math.sqrt(dx * dx + dy * dy) / R;
          if (d < 1) {
            const i = r * cols + c;
            heat[i] = Math.min(1, heat[i] + (1 - d) * (1 - d) * 0.5);
          }
        }
      }
    };

    const onMove = (e: PointerEvent) => {
      const x = e.clientX;
      const y = e.clientY;
      if (prev) {
        const dx = x - prev.x;
        const dy = y - prev.y;
        const steps = Math.min(40, Math.ceil(Math.hypot(dx, dy) / (spacing * 0.6)));
        for (let s = 1; s <= steps; s++) stamp(prev.x + (dx * s) / steps, prev.y + (dy * s) / steps);
      } else {
        stamp(x, y);
      }
      prev = { x, y };
    };
    const onLeave = () => {
      prev = null;
    };

    const draw = (now: number) => {
      const dt = Math.min(now - last, 50);
      last = now;
      const t = reduce ? 0 : (now - start) / 1000;
      const scrollY = window.scrollY;
      const decay = Math.exp(-dt / 650);

      // Clusters that are currently on screen (they move slower than the page).
      const sigmaBase = 0.28 * Math.min(w, h * 1.3);
      const live: LiveBlob[] = [];
      for (let i = 0; i < BLOBS.length; i++) {
        const b = BLOBS[i];
        const s = sigmaBase * b.s;
        const cx = b.x * w + Math.sin(t * 0.12 + i * 1.3) * 0.04 * w;
        const cy = b.y * h - scrollY * 0.55 + Math.cos(t * 0.1 + i * 1.7) * 0.03 * h;
        if (cy < -s * 2.6 || cy > h + s * 2.6) continue;
        live.push({ cx, cy, inv: 1 / (2 * s * s), a: b.a, i });
      }

      ctx.clearRect(0, 0, w, h);
      const paths: Path2D[] = [];
      for (let i = 0; i < LEVELS; i++) paths.push(new Path2D());

      for (let r = 0; r < rows; r++) {
        const y = r * spacing;
        for (let c = 0; c < cols; c++) {
          const idx = r * cols + c;
          const x = c * spacing;

          let e = 0.045 * (1 + Math.sin(t * 1.1 + phase[idx])); // shimmer

          for (let k = 0; k < live.length; k++) {
            const b = live[k];
            const dx = x - b.cx;
            const dy = y - b.cy;
            const d2 = dx * dx + dy * dy;
            const g = Math.exp(-d2 * b.inv);
            if (g > 0.01) {
              const wave = 0.78 + 0.22 * Math.sin(Math.sqrt(d2) * 0.035 - t * 0.7 + b.i);
              e += b.a * g * wave;
            }
          }

          let hv = heat[idx];
          if (hv > 0.003) {
            hv *= decay;
            heat[idx] = hv;
            e += hv;
          } else if (hv !== 0) {
            heat[idx] = 0;
          }

          if (e > 1) e = 1;
          const level = Math.min(LEVELS - 1, Math.floor(e * LEVELS));
          const rad = 0.8 + e * 2.0;
          const p = paths[level];
          p.moveTo(x + rad, y);
          p.arc(x, y, rad, 0, Math.PI * 2);
        }
      }

      for (let i = 0; i < LEVELS; i++) {
        ctx.fillStyle = styles[i];
        ctx.fill(paths[i]);
      }
    };

    resize();

    if (reduce) {
      // Static field; redraw only when the size or scroll position changes.
      let pending = false;
      const once = () => {
        if (pending) return;
        pending = true;
        raf = requestAnimationFrame((n) => {
          pending = false;
          draw(n);
        });
      };
      once();
      const onResize = () => {
        resize();
        once();
      };
      window.addEventListener("resize", onResize);
      window.addEventListener("scroll", once, { passive: true });
      return () => {
        cancelAnimationFrame(raf);
        window.removeEventListener("resize", onResize);
        window.removeEventListener("scroll", once);
      };
    }

    const loop = (now: number) => {
      draw(now);
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);

    window.addEventListener("resize", resize);
    window.addEventListener("pointermove", onMove, { passive: true });
    document.documentElement.addEventListener("mouseleave", onLeave);
    window.addEventListener("blur", onLeave);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
      window.removeEventListener("pointermove", onMove);
      document.documentElement.removeEventListener("mouseleave", onLeave);
      window.removeEventListener("blur", onLeave);
    };
  }, []);

  return (
    <div aria-hidden="true" className="pointer-events-none fixed inset-0 z-0 bg-[#05080D]">
      <canvas ref={canvasRef} className="absolute inset-0 block" />
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse at 50% 35%, rgba(5,8,13,0) 0%, rgba(5,8,13,0.55) 100%)",
        }}
      />
    </div>
  );
}