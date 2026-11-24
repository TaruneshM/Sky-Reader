import { useEffect, useRef } from "react";

/**
 * WeatherAtmosphere:
 * High-performance, eye-friendly canvas-based meteorological particle simulation.
 * Supported scenes: 'sun', 'rain', 'stars', 'wind', 'snow', 'thunder', 'clouds'.
 */
export default function WeatherAtmosphere({ scene = "none", isNight = true }) {
  if (scene === "none") return null;
  return <ParticleCanvas scene={scene} isNight={isNight} />;
}

function ParticleCanvas({ scene, isNight }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId;
    const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const handleResize = () => {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
      initScene();
      if (!document.hidden) render();
    };

    window.addEventListener("resize", handleResize);

    // Particles collections
    let rainDrops = [];
    let rainSplashes = [];
    let stars = [];
    let shootingStar = null;
    let leaves = [];
    let snowflakes = [];
    let sunMotes = [];
    let cloudBlobs = [];
    let lightningFlash = 0;
    let lastLightningTime = Date.now();

    // Leaf image shape drawer
    const drawLeaf = (ctx, x, y, size, angle, color) => {
      ctx.save();
      ctx.translate(x, y);
      ctx.rotate(angle);
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.moveTo(0, -size);
      ctx.quadraticCurveTo(size * 0.7, -size * 0.3, size * 0.3, size * 0.7);
      ctx.quadraticCurveTo(0, size, 0, size);
      ctx.quadraticCurveTo(0, size, -size * 0.3, size * 0.7);
      ctx.quadraticCurveTo(-size * 0.7, -size * 0.3, 0, -size);
      ctx.fill();
      ctx.restore();
    };

    // Initialize scenes
    const initScene = () => {
      // 1. Rain
      if (scene === "rain" || scene === "thunder") {
        rainDrops = Array.from({ length: Math.floor(width * 0.12) }, () => ({
          x: Math.random() * (width + 200) - 100,
          y: Math.random() * height,
          length: Math.random() * 20 + 15,
          speed: Math.random() * 12 + 18,
          opacity: Math.random() * 0.35 + 0.2,
          thickness: Math.random() * 1.2 + 0.8,
        }));
        rainSplashes = [];
      }

      // 2. Stars
      if (scene === "stars" || (scene === "wind" && isNight)) {
        stars = Array.from({ length: Math.floor(width * 0.15) }, () => ({
          x: Math.random() * width,
          y: Math.random() * height * 0.85,
          radius: Math.random() * 1.4 + 0.5,
          baseAlpha: Math.random() * 0.7 + 0.2,
          twinkleSpeed: Math.random() * 0.03 + 0.01,
          phase: Math.random() * Math.PI * 2,
          color:
            Math.random() > 0.8
              ? "rgba(186, 230, 253, "
              : Math.random() > 0.6
              ? "rgba(253, 230, 138, "
              : "rgba(255, 255, 255, ",
        }));
        shootingStar = null;
      }

      // 3. Wind / Blowing Leaves
      if (scene === "wind") {
        const leafColors = [
          "rgba(251, 146, 60, 0.75)",  // Amber / orange
          "rgba(234, 88, 12, 0.7)",   // Rust red
          "rgba(202, 138, 4, 0.75)",  // Golden olive
          "rgba(52, 211, 153, 0.65)", // Sage green
          "rgba(245, 158, 11, 0.7)",  // Warm yellow
        ];
        leaves = Array.from({ length: 32 }, () => ({
          x: Math.random() * width,
          y: Math.random() * height,
          size: Math.random() * 10 + 9,
          angle: Math.random() * Math.PI * 2,
          rotationSpeed: (Math.random() - 0.5) * 0.08,
          vx: Math.random() * 3 + 4,
          vy: Math.random() * 1.5 + 1,
          wobbleFreq: Math.random() * 0.03 + 0.015,
          wobbleAmp: Math.random() * 2 + 1,
          color: leafColors[Math.floor(Math.random() * leafColors.length)],
        }));
      }

      // 4. Sunshine Motes
      if (scene === "sun") {
        sunMotes = Array.from({ length: 45 }, () => ({
          x: Math.random() * width,
          y: Math.random() * height,
          radius: Math.random() * 3 + 1,
          alpha: Math.random() * 0.5 + 0.2,
          vx: (Math.random() - 0.5) * 0.4,
          vy: -Math.random() * 0.6 - 0.2,
          pulse: Math.random() * Math.PI,
        }));
      }

      // 5. Snow
      if (scene === "snow") {
        snowflakes = Array.from({ length: Math.floor(width * 0.1) }, () => ({
          x: Math.random() * width,
          y: Math.random() * height,
          radius: Math.random() * 3 + 1.2,
          density: Math.random() * 1.5 + 0.5,
          alpha: Math.random() * 0.6 + 0.3,
          swing: Math.random() * Math.PI * 2,
          swingSpeed: Math.random() * 0.02 + 0.01,
        }));
      }

      // 6. Layered Clouds
      if (scene === "clouds") {
        cloudBlobs = Array.from({ length: 12 }, () => ({
          x: Math.random() * (width + 400) - 200,
          y: Math.random() * (height * 0.65),
          radius: Math.random() * 120 + 80,
          speed: Math.random() * 0.3 + 0.15,
          alpha: Math.random() * 0.08 + 0.04,
        }));
      }
    };

    initScene();

    let angleCounter = 0;

    // Render Loop
    const render = () => {
      ctx.clearRect(0, 0, width, height);
      angleCounter += 0.01;

      // -------------------------------------------------------------------
      // 1. SCENE: SUNSHINE & WARM SOLAR RAYS
      // -------------------------------------------------------------------
      if (scene === "sun") {
        const sunX = width * 0.85;
        const sunY = height * 0.15;

        // Radiant sun core & pulsating atmospheric flare
        const sunGlow = ctx.createRadialGradient(sunX, sunY, 10, sunX, sunY, width * 0.65);
        sunGlow.addColorStop(0, "rgba(253, 224, 71, 0.22)");
        sunGlow.addColorStop(0.3, "rgba(251, 146, 60, 0.10)");
        sunGlow.addColorStop(0.7, "rgba(251, 191, 36, 0.03)");
        sunGlow.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.fillStyle = sunGlow;
        ctx.fillRect(0, 0, width, height);

        // Soft rotating sunbeams
        ctx.save();
        ctx.translate(sunX, sunY);
        ctx.rotate(angleCounter * 0.05);
        ctx.fillStyle = "rgba(254, 240, 138, 0.025)";
        for (let i = 0; i < 8; i++) {
          ctx.beginPath();
          ctx.moveTo(0, 0);
          ctx.arc(0, 0, width * 0.8, (i * Math.PI) / 4, (i * Math.PI) / 4 + Math.PI / 10);
          ctx.fill();
        }
        ctx.restore();

        // Warm floating solar dust motes
        sunMotes.forEach((mote) => {
          mote.x += mote.vx;
          mote.y += mote.vy;
          mote.pulse += 0.02;
          if (mote.y < -10) mote.y = height + 10;
          if (mote.x < -10) mote.x = width + 10;
          if (mote.x > width + 10) mote.x = -10;

          const currentAlpha = mote.alpha * (0.6 + 0.4 * Math.sin(mote.pulse));
          ctx.beginPath();
          ctx.arc(mote.x, mote.y, mote.radius, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(253, 224, 71, ${currentAlpha})`;
          ctx.shadowBlur = 8;
          ctx.shadowColor = "rgba(251, 191, 36, 0.6)";
          ctx.fill();
          ctx.shadowBlur = 0;
        });
      }

      // -------------------------------------------------------------------
      // 2. SCENE: RAIN & THUNDER
      // -------------------------------------------------------------------
      if (scene === "rain" || scene === "thunder") {
        // Distant sheet lightning flash (soft, eye-friendly, infrequent)
        if (scene === "thunder") {
          const now = Date.now();
          if (now - lastLightningTime > 7000 && Math.random() < 0.02) {
            lightningFlash = 0.35;
            lastLightningTime = now;
          }
          if (lightningFlash > 0) {
            ctx.fillStyle = `rgba(196, 181, 253, ${lightningFlash})`;
            ctx.fillRect(0, 0, width, height);
            lightningFlash *= 0.88;
            if (lightningFlash < 0.01) lightningFlash = 0;
          }
        }

        // Draw raindrops
        ctx.lineWidth = 1.2;
        const rainSlant = 2.5;

        rainDrops.forEach((drop) => {
          ctx.beginPath();
          ctx.moveTo(drop.x, drop.y);
          ctx.lineTo(drop.x + rainSlant, drop.y + drop.length);
          ctx.strokeStyle = `rgba(186, 230, 253, ${drop.opacity})`;
          ctx.stroke();

          drop.x += rainSlant * 0.7;
          drop.y += drop.speed;

          // Splash at ground
          if (drop.y > height - 30) {
            if (rainSplashes.length < 25 && Math.random() > 0.7) {
              rainSplashes.push({
                x: drop.x,
                y: height - Math.random() * 20,
                radius: 1,
                maxRadius: Math.random() * 7 + 4,
                alpha: 0.5,
              });
            }
            drop.y = -drop.length;
            drop.x = Math.random() * (width + 200) - 100;
          }
        });

        // Draw splash ripples
        for (let i = rainSplashes.length - 1; i >= 0; i--) {
          const sp = rainSplashes[i];
          ctx.beginPath();
          ctx.ellipse(sp.x, sp.y, sp.radius * 1.6, sp.radius * 0.5, 0, 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(186, 230, 253, ${sp.alpha})`;
          ctx.lineWidth = 0.8;
          ctx.stroke();
          sp.radius += 0.5;
          sp.alpha -= 0.025;
          if (sp.alpha <= 0) {
            rainSplashes.splice(i, 1);
          }
        }
      }

      // -------------------------------------------------------------------
      // 3. SCENE: MIDNIGHT STARS & TWINKLING SKY
      // -------------------------------------------------------------------
      if (scene === "stars" || (scene === "wind" && isNight)) {
        // Twinkling stars
        stars.forEach((star) => {
          star.phase += star.twinkleSpeed;
          const currentAlpha = star.baseAlpha + Math.sin(star.phase) * 0.25;
          const a = Math.max(0.1, Math.min(currentAlpha, 0.95));

          ctx.beginPath();
          ctx.arc(star.x, star.y, star.radius, 0, Math.PI * 2);
          ctx.fillStyle = `${star.color}${a})`;
          ctx.fill();
        });

        // Occasional gentle shooting star
        if (!shootingStar && Math.random() < 0.005) {
          shootingStar = {
            x: Math.random() * width * 0.8,
            y: Math.random() * height * 0.4,
            length: Math.random() * 80 + 70,
            speed: Math.random() * 10 + 14,
            vx: Math.random() * 8 + 8,
            vy: Math.random() * 5 + 4,
            opacity: 0.8,
          };
        }

        if (shootingStar) {
          ctx.beginPath();
          ctx.moveTo(shootingStar.x, shootingStar.y);
          ctx.lineTo(
            shootingStar.x - shootingStar.vx * 3,
            shootingStar.y - shootingStar.vy * 3
          );
          ctx.strokeStyle = `rgba(224, 231, 255, ${shootingStar.opacity})`;
          ctx.lineWidth = 1.6;
          ctx.stroke();

          shootingStar.x += shootingStar.vx;
          shootingStar.y += shootingStar.vy;
          shootingStar.opacity -= 0.02;

          if (
            shootingStar.opacity <= 0 ||
            shootingStar.x > width ||
            shootingStar.y > height
          ) {
            shootingStar = null;
          }
        }
      }

      // -------------------------------------------------------------------
      // 4. SCENE: BREEZE & BLOWING LEAVES
      // -------------------------------------------------------------------
      if (scene === "wind") {
        // Wind streamlines (subtle atmospheric air currents)
        ctx.strokeStyle = "rgba(226, 232, 240, 0.07)";
        ctx.lineWidth = 1.2;
        for (let i = 0; i < 3; i++) {
          const streamY = height * (0.2 + i * 0.3) + Math.sin(angleCounter + i) * 20;
          ctx.beginPath();
          ctx.moveTo(-100, streamY);
          ctx.bezierCurveTo(
            width * 0.3,
            streamY - 40,
            width * 0.6,
            streamY + 40,
            width + 100,
            streamY - 10
          );
          ctx.stroke();
        }

        // Tumbling and fluttering leaves
        leaves.forEach((leaf) => {
          leaf.angle += leaf.rotationSpeed;
          leaf.x += leaf.vx + Math.sin(angleCounter * leaf.wobbleFreq) * leaf.wobbleAmp;
          leaf.y += leaf.vy + Math.cos(angleCounter * leaf.wobbleFreq) * 0.8;

          if (leaf.x > width + 40) {
            leaf.x = -40;
            leaf.y = Math.random() * height;
          }
          if (leaf.y > height + 40) {
            leaf.y = -40;
            leaf.x = Math.random() * width;
          }

          drawLeaf(ctx, leaf.x, leaf.y, leaf.size, leaf.angle, leaf.color);
        });
      }

      // -------------------------------------------------------------------
      // 5. SCENE: SNOWFLAKES DRIFTING
      // -------------------------------------------------------------------
      if (scene === "snow") {
        snowflakes.forEach((flake) => {
          flake.swing += flake.swingSpeed;
          flake.y += flake.density;
          flake.x += Math.sin(flake.swing) * 0.8 + 0.3;

          if (flake.y > height + 10) {
            flake.y = -10;
            flake.x = Math.random() * width;
          }

          ctx.beginPath();
          ctx.arc(flake.x, flake.y, flake.radius, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(240, 249, 255, ${flake.alpha})`;
          ctx.fill();
        });
      }

      // -------------------------------------------------------------------
      // 6. SCENE: LAYERED OVERCAST CLOUDS
      // -------------------------------------------------------------------
      if (scene === "clouds") {
        cloudBlobs.forEach((cloud) => {
          cloud.x += cloud.speed;
          if (cloud.x > width + cloud.radius * 2) {
            cloud.x = -cloud.radius * 2;
            cloud.y = Math.random() * (height * 0.65);
          }

          const grad = ctx.createRadialGradient(
            cloud.x,
            cloud.y,
            cloud.radius * 0.2,
            cloud.x,
            cloud.y,
            cloud.radius
          );
          grad.addColorStop(0, `rgba(203, 213, 225, ${cloud.alpha})`);
          grad.addColorStop(1, "rgba(203, 213, 225, 0)");

          ctx.fillStyle = grad;
          ctx.beginPath();
          ctx.arc(cloud.x, cloud.y, cloud.radius, 0, Math.PI * 2);
          ctx.fill();
        });
      }

      if (!document.hidden) {
        animationFrameId = requestAnimationFrame(render);
      }
    };

    const syncMotion = () => {
      cancelAnimationFrame(animationFrameId);
      if (!document.hidden) render();
    };
    document.addEventListener("visibilitychange", syncMotion);
    syncMotion();

    return () => {
      cancelAnimationFrame(animationFrameId);
      document.removeEventListener("visibilitychange", syncMotion);
      window.removeEventListener("resize", handleResize);
    };
  }, [scene, isNight]);

  return (
    <div className={`weather-atmosphere-canvas-wrapper scene-${scene}`}>
      <canvas ref={canvasRef} className="weather-atmosphere-canvas" />
    </div>
  );
}
