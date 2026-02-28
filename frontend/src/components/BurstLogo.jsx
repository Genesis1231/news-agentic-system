const BurstLogo = ({ size = 30 }) => {
  const cx = 8; // vertical center
  const bars = [
    { x: 0,  h: 7  },
    { x: 6,  h: 18 },
    { x: 12, h: 11 },
    { x: 18, h: 5  },
  ];

  return (
    <svg viewBox="0 0 22 16" width={size} height={size} fill="none">
      {bars.map((bar, i) => (
        <rect
          key={i}
          x={bar.x}
          y={cx - bar.h / 2 + 1}
          width="4"
          height={bar.h}
          rx="2"
          fill="#7C3AED"
        />
      ))}
    </svg>
  );
};

export default BurstLogo;
