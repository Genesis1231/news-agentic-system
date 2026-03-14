import { useCallback, useEffect, useRef, useState } from 'react';
import Particles from '@tsparticles/react';
import { loadSlim } from '@tsparticles/slim';

const BASE_OPTIONS = {
  fullScreen: { enable: false },
  background: { color: 'transparent' },
  fpsLimit: 60,
  detectRetina: true,
  particles: {
    number: { value: 120 },
    color: { value: ['#7c3aed', '#a78bfa', '#6d28d9', '#8b5cf6', '#c4b5fd'] },
    shape: { type: 'circle' },
    opacity: { value: { min: 0.03, max: 0.3 } },
    size: { value: { min: 0.5, max: 3 } },
    move: {
      enable: true,
      speed: 0.4,
      direction: 'none',
      outModes: { default: 'out' },
      random: true,
    },
    links: { enable: false },
  },
};

const AudioParticles = ({ isPlaying, audioRef }) => {
  const containerRef = useRef(null);
  const analyserRef = useRef(null);
  const audioCtxRef = useRef(null);
  const sourceRef = useRef(null);
  const frameRef = useRef(null);
  const [engineReady, setEngineReady] = useState(false);

  const init = useCallback(async (engine) => {
    await loadSlim(engine);
    setEngineReady(true);
  }, []);

  const loaded = useCallback((container) => {
    containerRef.current = container;
  }, []);

  // Connect Web Audio API to audio element
  useEffect(() => {
    const audio = audioRef?.current;
    if (!audio) return;

    // Only create context once
    if (audioCtxRef.current) return;

    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 256;
    analyser.smoothingTimeConstant = 0.8;

    const source = ctx.createMediaElementSource(audio);
    source.connect(analyser);
    analyser.connect(ctx.destination);

    audioCtxRef.current = ctx;
    analyserRef.current = analyser;
    sourceRef.current = source;

    return () => {
      ctx.close();
      audioCtxRef.current = null;
      analyserRef.current = null;
    };
  }, [audioRef]);

  // Animation loop — drive particles from audio intensity
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const dataArray = analyserRef.current
      ? new Uint8Array(analyserRef.current.frequencyBinCount)
      : null;

    const animate = () => {
      const particles = container.particles?.array;
      if (!particles?.length) {
        frameRef.current = requestAnimationFrame(animate);
        return;
      }

      let intensity = 0;

      if (isPlaying && analyserRef.current && dataArray) {
        // Real audio intensity from AnalyserNode
        analyserRef.current.getByteFrequencyData(dataArray);
        const sum = dataArray.reduce((a, b) => a + b, 0);
        intensity = sum / (dataArray.length * 255);
      } else if (isPlaying) {
        // Simulated intensity when no real audio connected
        const t = Date.now() / 1000;
        intensity = 0.3 + Math.sin(t * 1.8) * 0.12 + Math.sin(t * 4.3) * 0.08;
      }

      // Scale factor from intensity (matches Python: intensity^0.5 * 3)
      const factor = Math.sqrt(Math.max(intensity, 0)) * 3;

      particles.forEach((p) => {
        if (isPlaying) {
          // Add audio-reactive velocity (like Python: random * intensity * 0.8)
          p.velocity.x += (Math.random() - 0.5) * factor * 0.15;
          p.velocity.y += (Math.random() - 0.5) * factor * 0.15;
          // Damping (Python uses 0.85)
          p.velocity.x *= 0.92;
          p.velocity.y *= 0.92;
          // Size pulse
          if (p.size) {
            p.size.value = p.size.min + (p.size.max - p.size.min) * (0.3 + factor * 0.25);
          }
        } else {
          // Settle to calm state
          p.velocity.x *= 0.97;
          p.velocity.y *= 0.97;
        }
      });

      frameRef.current = requestAnimationFrame(animate);
    };

    animate();
    return () => {
      if (frameRef.current) cancelAnimationFrame(frameRef.current);
    };
  }, [isPlaying, engineReady]);

  return (
    <Particles
      id="audio-particles"
      init={init}
      loaded={loaded}
      options={BASE_OPTIONS}
      className="!absolute !inset-0 !w-full !h-full"
    />
  );
};

export default AudioParticles;
