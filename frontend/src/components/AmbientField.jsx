import { useEffect, useRef } from "react";

/**
 * AmbientField — An ultra-modern, fresh & vibrant interactive Cosmic Aurora mesh.
 * Features:
 * - Fluid undulating neon aurora waves (fuchsia, electric cyan, violet, vivid emerald)
 * - Interactive cursor-following glow & particle dust
 * - Subtle geometric holographic depth
 */
export default function AmbientField({ theme }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;
    const ctx = canvas.getContext("2d");
    if (!ctx) return undefined;

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let width = 0;
    let height = 0;
    let dpr = 1;
    let frame = 0;
    let mouse = { x: -1000, y: -1000, targetX: -1000, targetY: -1000 };

    // Floating vibrant plasma orbs
    const orbs = [
      {
        baseX: 0.2,
        baseY: 0.25,
        radius: 420,
        color: [99, 102, 241], // Electric Indigo
        alpha: 0.35,
        speedX: 0.0008,
        speedY: 0.0011,
      },
      {
        baseX: 0.8,
        baseY: 0.3,
        radius: 460,
        color: [236, 72, 153], // Radiant Neon Fuchsia / Pink
        alpha: 0.28,
        speedX: -0.0009,
        speedY: 0.0014,
      },
      {
        baseX: 0.5,
        baseY: 0.75,
        radius: 500,
        color: [6, 182, 212], // Luminous Cyan
        alpha: 0.32,
        speedX: 0.0012,
        speedY: -0.0007,
      },
      {
        baseX: 0.85,
        baseY: 0.85,
        radius: 380,
        color: [16, 185, 129], // Vivid Emerald
        alpha: 0.22,
        speedX: -0.0011,
        speedY: -0.0009,
      },
      {
        baseX: 0.15,
        baseY: 0.8,
        radius: 360,
        color: [168, 85, 247], // Bright Purple
        alpha: 0.3,
        speedX: 0.001,
        speedY: 0.0008,
      },
    ];

    // Star / cosmic dust particles
    let particles = [];

    function resize() {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      canvas.style.width = width + "px";
      canvas.style.height = height + "px";
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      const count = Math.round(Math.min(70, Math.max(30, (width * height) / 22000)));
      particles = Array.from({ length: count }, () => ({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.3,
        size: 0.8 + Math.random() * 2.2,
        color: Math.random() > 0.5 ? "rgba(6, 182, 212, " : "rgba(236, 72, 153, ",
        alpha: 0.3 + Math.random() * 0.5,
        pulseOffset: Math.random() * Math.PI * 2,
      }));
    }

    function onMouseMove(e) {
      const rect = canvas.getBoundingClientRect();
      mouse.targetX = e.clientX - rect.left;
      mouse.targetY = e.clientY - rect.top;
    }

    function onMouseLeave() {
      mouse.targetX = -1000;
      mouse.targetY = -1000;
    }

    function draw() {
      ctx.clearRect(0, 0, width, height);

      // Smooth mouse interpolation
      mouse.x += (mouse.targetX - mouse.x) * 0.05;
      mouse.y += (mouse.targetY - mouse.y) * 0.05;

      // 1. Draw glowing vibrant aurora orbs
      const isLight = theme === "light";
      ctx.globalCompositeOperation = isLight ? "multiply" : "screen";

      for (let i = 0; i < orbs.length; i++) {
        const orb = orbs[i];
        const t = frame;
        const currentX = (orb.baseX + Math.sin(t * orb.speedX + i) * 0.18) * width;
        const currentY = (orb.baseY + Math.cos(t * orb.speedY + i * 2) * 0.18) * height;

        const grad = ctx.createRadialGradient(
          currentX,
          currentY,
          0,
          currentX,
          currentY,
          orb.radius
        );

        const [r, g, b] = orb.color;
        const alphaFactor = isLight ? 0.14 : orb.alpha;
        grad.addColorStop(0, `rgba(${r}, ${g}, ${b}, ${alphaFactor})`);
        grad.addColorStop(0.5, `rgba(${r}, ${g}, ${b}, ${alphaFactor * 0.4})`);
        grad.addColorStop(1, "rgba(0, 0, 0, 0)");

        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(currentX, currentY, orb.radius, 0, Math.PI * 2);
        ctx.fill();
      }

      // 2. Interactive cursor glow
      if (mouse.x > -500) {
        const mouseGrad = ctx.createRadialGradient(
          mouse.x,
          mouse.y,
          0,
          mouse.x,
          mouse.y,
          260
        );
        const mAlpha = isLight ? 0.12 : 0.3;
        mouseGrad.addColorStop(0, `rgba(6, 182, 212, ${mAlpha})`);
        mouseGrad.addColorStop(0.4, `rgba(236, 72, 153, ${mAlpha * 0.5})`);
        mouseGrad.addColorStop(1, "rgba(0, 0, 0, 0)");

        ctx.fillStyle = mouseGrad;
        ctx.beginPath();
        ctx.arc(mouse.x, mouse.y, 260, 0, Math.PI * 2);
        ctx.fill();
      }

      // 3. Connect close particles with subtle neon threads
      ctx.globalCompositeOperation = "source-over";
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.hypot(dx, dy);

          if (dist < 110) {
            const alpha = (1 - dist / 110) * (isLight ? 0.1 : 0.18);
            ctx.strokeStyle = isLight
              ? `rgba(124, 58, 237, ${alpha})`
              : `rgba(168, 85, 247, ${alpha})`;
            ctx.lineWidth = 0.8;
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.stroke();
          }
        }
      }

      // 4. Draw sparkling cosmic dust particles
      for (const p of particles) {
        const pulse = 0.6 + 0.4 * Math.sin(frame * 0.03 + p.pulseOffset);
        ctx.fillStyle = `${p.color}${p.alpha * pulse})`;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    function step() {
      // Update particles
      for (const p of particles) {
        p.x += p.vx;
        p.y += p.vy;

        // Soft attraction to cursor
        if (mouse.x > -500) {
          const dx = mouse.x - p.x;
          const dy = mouse.y - p.y;
          const dist = Math.hypot(dx, dy);
          if (dist < 180 && dist > 10) {
            p.x += (dx / dist) * 0.4;
            p.y += (dy / dist) * 0.4;
          }
        }

        if (p.x < -10) p.x = width + 10;
        if (p.x > width + 10) p.x = -10;
        if (p.y < -10) p.y = height + 10;
        if (p.y > height + 10) p.y = -10;
      }

      frame += 1;
      draw();
    }

    let raf = 0;
    function loop() {
      step();
      raf = window.requestAnimationFrame(loop);
    }

    function start() {
      if (raf || reduceMotion) return;
      raf = window.requestAnimationFrame(loop);
    }

    function stop() {
      if (!raf) return;
      window.cancelAnimationFrame(raf);
      raf = 0;
    }

    function onVisibility() {
      if (document.hidden) stop();
      else start();
    }

    function onResize() {
      resize();
      draw();
    }

    resize();
    draw();
    if (!reduceMotion) start();

    window.addEventListener("resize", onResize);
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseleave", onMouseLeave);
    document.addEventListener("visibilitychange", onVisibility);

    return () => {
      stop();
      window.removeEventListener("resize", onResize);
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseleave", onMouseLeave);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [theme]);

  return <canvas ref={canvasRef} className="ambient" aria-hidden="true" />;
}
