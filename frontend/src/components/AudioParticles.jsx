import { useEffect, useRef, useCallback } from 'react';

const N_PARTICLES = 120;
const DAMPING = 0.85;

function createParticles(w, h) {
  const cx = w / 2, cy = h * 0.38;
  const particles = [];
  for (let i = 0; i < N_PARTICLES; i++) {
    const angle = (2 * Math.PI * i) / N_PARTICLES;
    particles.push({
      x: cx, y: cy,
      vx: Math.cos(angle) * 1.5,
      vy: Math.sin(angle) * 1.5,
      baseSize: Math.random() * 2.5 + 0.8,
      size: 1,
      radiusMul: Math.random() * 0.5 + 0.75,
    });
  }
  return particles;
}

function updateParticles(particles, intensity, frame, w, h) {
  const cx = w / 2, cy = h * 0.38;
  const safe = Math.max(intensity, 0);
  const factor = Math.sqrt(safe) * 3;
  const t = frame * 0.03;

  for (let i = 0; i < particles.length; i++) {
    const p = particles[i];
    const baseRadius = 60 + factor * 35;
    const radius = baseRadius * p.radiusMul;

    const angle = t + (2 * Math.PI * i) / particles.length;
    const a = i % 3 === 0 ? t * 1.5 + (2 * Math.PI * i) / particles.length : angle;

    const tx = cx + Math.cos(a) * radius;
    const ty = cy + Math.sin(a) * radius * 1.2;

    p.vx += (tx - p.x) * (0.02 + factor * 0.02);
    p.vy += (ty - p.y) * (0.02 + factor * 0.02);
    p.vx += (Math.random() - 0.5) * factor * 0.8;
    p.vy += (Math.random() - 0.5) * factor * 0.8;

    p.x += p.vx * (1 + factor * 0.5);
    p.y += p.vy * (1 + factor * 0.5);
    p.vx *= DAMPING;
    p.vy *= DAMPING;
    p.size = p.baseSize * (1 + factor * 0.8);

    if (p.x < 0) p.x += w;
    if (p.x > w) p.x -= w;
    if (p.y < 0) p.y += h;
    if (p.y > h) p.y -= h;
  }
  return factor;
}

function drawParticles(ctx, particles, factor) {
  ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
  for (const p of particles) {
    const r = Math.min(Math.round(124 + factor * 50), 180);
    const g = Math.min(Math.round(58 + factor * 80), 160);
    const b = Math.min(Math.round(237 + factor * 18), 255);
    const a = Math.min(0.25 + factor * 0.25, 0.8);
    ctx.beginPath();
    ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(${r},${g},${b},${a})`;
    ctx.fill();
  }
}

const AudioParticles = ({ isPlaying, audioRef }) => {
  const canvasRef = useRef(null);
  const particlesRef = useRef(null);
  const frameRef = useRef(0);
  const rafRef = useRef(null);
  const analyserRef = useRef(null);
  const audioCtxRef = useRef(null);
  const useAnalyserRef = useRef(false);

  // Try to connect analyser — works for same-origin audio, fails silently for cross-origin
  const ensureAnalyser = useCallback(() => {
    if (analyserRef.current) return;
    const audio = audioRef?.current;
    if (!audio) return;

    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.8;

      const source = ctx.createMediaElementSource(audio);
      source.connect(analyser);
      analyser.connect(ctx.destination);

      audioCtxRef.current = ctx;
      analyserRef.current = analyser;
      useAnalyserRef.current = true;
    } catch (e) {
      // Cross-origin or other issue — fall back to simulated intensity
      useAnalyserRef.current = false;
    }
  }, [audioRef]);

  useEffect(() => {
    if (isPlaying) {
      ensureAnalyser();
      if (audioCtxRef.current?.state === 'suspended') {
        audioCtxRef.current.resume();
      }
    }
  }, [isPlaying, ensureAnalyser]);

  // Canvas resize
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const resize = () => {
      const rect = canvas.parentElement.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      canvas.style.width = rect.width + 'px';
      canvas.style.height = rect.height + 'px';
      canvas.getContext('2d').scale(dpr, dpr);
      particlesRef.current = createParticles(rect.width, rect.height);
    };

    resize();
    window.addEventListener('resize', resize);
    return () => window.removeEventListener('resize', resize);
  }, []);

  // Animation loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const dataArray = new Uint8Array(128);

    const animate = () => {
      if (!particlesRef.current) {
        rafRef.current = requestAnimationFrame(animate);
        return;
      }

      let intensity = 0;

      if (isPlaying && useAnalyserRef.current && analyserRef.current) {
        // Real audio data available (same-origin)
        analyserRef.current.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) sum += dataArray[i];
        intensity = sum / (dataArray.length * 255);
        // If analyser returns all zeros (CORS tainted), switch to simulation
        if (intensity === 0) {
          useAnalyserRef.current = false;
        }
      }

      if (isPlaying && !useAnalyserRef.current) {
        // Simulated intensity — organic pulsing
        const t = Date.now() / 1000;
        intensity = 0.3 + Math.sin(t * 1.8) * 0.12 + Math.sin(t * 4.3) * 0.08;
      }

      if (!isPlaying) {
        intensity = 0.02;
      }

      const rect = canvas.parentElement.getBoundingClientRect();
      const factor = updateParticles(particlesRef.current, intensity, frameRef.current, rect.width, rect.height);
      drawParticles(ctx, particlesRef.current, factor);
      frameRef.current++;
      rafRef.current = requestAnimationFrame(animate);
    };

    animate();
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); };
  }, [isPlaying]);

  // Cleanup
  useEffect(() => {
    return () => audioCtxRef.current?.close();
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full pointer-events-none"
    />
  );
};

export default AudioParticles;
