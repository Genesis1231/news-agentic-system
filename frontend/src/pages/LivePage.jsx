import { useState, useEffect, useMemo, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Play, Pause, ChevronDown, ChevronUp } from 'lucide-react';
import { format } from 'date-fns';
import BurstLogo from '../components/BurstLogo';
import { MOCK_STORIES, CATEGORIES, DEPTH_CONFIG } from '../data/mockStories';

const BAR_COUNT = 48;
const CATEGORY_KEYS = new Set(CATEGORIES.map((c) => c.key));

// Unified tag list: categories first, then unique entities
const ALL_TAGS = [
  ...CATEGORIES.map((c) => ({ label: c.label, value: c.key })),
  ...[...new Set(MOCK_STORIES.flatMap((s) => s.entities))].sort().map((e) => ({
    label: e,
    value: e,
  })),
];

const LivePage = () => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [progress, setProgress] = useState(0);
  const [activeFilter, setActiveFilter] = useState('ALL');
  const [expandedId, setExpandedId] = useState(null);
  const [filtersExpanded, setFiltersExpanded] = useState(false);

  const currentStory = MOCK_STORIES[currentIndex];
  const depth = DEPTH_CONFIG[currentStory.depth] || DEPTH_CONFIG.FLASH;

  const barScales = useMemo(
    () => Array.from({ length: BAR_COUNT }, () => 0.25 + Math.random() * 0.75),
    []
  );

  // Auto-advance through stories when playing
  useEffect(() => {
    if (!isPlaying) return;
    const id = setInterval(() => {
      setProgress((p) => {
        if (p >= 100) {
          setCurrentIndex((i) => (i + 1) % MOCK_STORIES.length);
          return 0;
        }
        return p + 0.15;
      });
    }, 100);
    return () => clearInterval(id);
  }, [isPlaying]);

  const toggleExpand = useCallback((id) => {
    setExpandedId((prev) => (prev === id ? null : id));
  }, []);

  const feedStories = useMemo(() => {
    const rest = MOCK_STORIES.filter((s) => s.id !== currentStory.id);
    if (activeFilter === 'ALL') return rest;
    if (CATEGORY_KEYS.has(activeFilter)) return rest.filter((s) => s.category.includes(activeFilter));
    return rest.filter((s) => s.entities.includes(activeFilter));
  }, [activeFilter, currentStory.id]);

  return (
    <div className="h-screen bg-black text-white flex flex-col overflow-hidden">
      <nav className="shrink-0 border-b border-white/[0.06] bg-black/60 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-8 py-6 flex items-center">
          <Link to="/" className="flex items-center gap-3 group">
            <BurstLogo size={28} />
            <span className="text-2xl font-semibold tracking-tight text-white/90 group-hover:text-white transition-colors">
              burst.fm
            </span>
          </Link>
        </div>
      </nav>

      {/* Mobile compact player */}
      <div className="md:hidden flex items-center gap-3 px-4 py-3 border-b border-white/[0.06] bg-black/90 shrink-0">
        <button
          onClick={() => setIsPlaying((p) => !p)}
          className="w-10 h-10 rounded-full bg-white/[0.08] border border-white/[0.12] flex items-center justify-center shrink-0"
        >
          {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
        </button>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">{currentStory.title}</p>
          <p className="text-xs text-purple-400/70">{currentStory.category[0]}</p>
        </div>
        <span className="relative flex h-2 w-2 shrink-0">
          <span className="absolute inset-0 rounded-full bg-red-500" style={{ animation: 'pulse-ring 1.5s ease-out infinite' }} />
          <span className="relative rounded-full h-2 w-2 bg-red-500" />
        </span>
      </div>

      {/* 50/50 split */}
      <div className="flex-1 min-h-0 flex justify-center">
        <div className="w-full max-w-7xl flex min-h-0">

          {/* LEFT: RADIO */}
          <aside className="hidden md:flex w-1/2 shrink-0 flex-col items-center justify-center relative overflow-hidden">
            <div
              className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/4 w-[400px] h-[400px] rounded-full blur-[120px] pointer-events-none transition-opacity duration-[2000ms]"
              style={{
                background: 'radial-gradient(circle, rgba(124,58,237,0.18) 0%, transparent 70%)',
                opacity: isPlaying ? 1 : 0.2,
              }}
            />

            <div className="relative flex flex-col items-center w-full px-12">
              <div className="flex items-center gap-2.5 px-4 py-2 rounded-full border border-red-500/20 bg-red-500/[0.06] mb-14">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="absolute inset-0 rounded-full bg-red-500" style={{ animation: 'pulse-ring 1.5s ease-out infinite' }} />
                  <span className="relative rounded-full h-2.5 w-2.5 bg-red-500" />
                </span>
                <span className="text-xs font-bold tracking-[0.25em] text-red-400 uppercase">On Air</span>
              </div>

              <div className="flex items-center justify-center gap-[3px] h-36 w-full max-w-[360px] mb-12">
                {barScales.map((scale, i) => (
                  <div
                    key={i}
                    className="w-[5px] rounded-full"
                    style={{
                      height: '100%',
                      background: isPlaying
                        ? 'linear-gradient(to top, rgba(124,58,237,0.5), rgba(167,139,250,0.9))'
                        : 'rgba(124,58,237,0.25)',
                      '--bar-scale': scale,
                      transform: isPlaying ? undefined : `scaleY(${0.15 + scale * 0.25})`,
                      animation: isPlaying
                        ? `waveform-bar ${0.8 + Math.random() * 1.0}s ease-in-out ${i * 0.035}s infinite`
                        : 'none',
                      transition: 'transform 0.6s ease, background 0.6s ease',
                      transformOrigin: 'center',
                    }}
                  />
                ))}
              </div>

              <button
                onClick={() => setIsPlaying((p) => !p)}
                className="w-16 h-16 rounded-full bg-white/[0.07] border border-white/[0.12] flex items-center justify-center hover:bg-white/[0.12] hover:border-white/[0.2] transition-all active:scale-95 mb-12"
              >
                {isPlaying ? <Pause className="w-6 h-6" /> : <Play className="w-6 h-6 ml-0.5" />}
              </button>

              <div className="text-center w-full max-w-[340px]">
                <div className="flex items-center justify-center gap-2.5 mb-4">
                  <span className="px-2.5 py-1 rounded text-xs font-bold tracking-wider uppercase bg-purple-500/10 text-purple-400 border border-purple-500/20">
                    {currentStory.category[0]}
                  </span>
                  <span className={`flex items-center gap-1.5 text-xs font-bold tracking-wider uppercase ${depth.color}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${depth.dot}`} />
                    {depth.label}
                  </span>
                </div>
                <h2 className="text-lg font-semibold leading-snug">
                  {currentStory.title}
                </h2>
              </div>
            </div>
          </aside>

          {/* RIGHT: FEED */}
          <main className="flex-1 min-w-0 flex flex-col">
            {/* Collapsible filter tags */}
            <div className="border-b border-white/[0.06] px-6 py-3 shrink-0">
              <div
                className="flex items-center gap-2 flex-wrap overflow-hidden"
                style={{ maxHeight: filtersExpanded ? 'none' : '4.5rem' }}
              >
                {ALL_TAGS.map(({ label, value }) => (
                  <button
                    key={value}
                    onClick={() => setActiveFilter(value)}
                    className={`shrink-0 px-3 py-1.5 rounded text-xs font-medium tracking-wide transition-colors border ${
                      activeFilter === value
                        ? 'bg-purple-500/15 text-purple-400 border-purple-500/30'
                        : 'bg-transparent text-zinc-500 border-transparent hover:text-zinc-300'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <button
                onClick={() => setFiltersExpanded((v) => !v)}
                className="mt-1.5 text-[11px] text-zinc-600 hover:text-zinc-400 transition-colors flex items-center gap-1"
              >
                {filtersExpanded
                  ? <>Less <ChevronUp className="w-3 h-3" /></>
                  : <>More tags <ChevronDown className="w-3 h-3" /></>
                }
              </button>
            </div>

            {/* Stories */}
            <div className="flex-1 overflow-y-auto" style={{ scrollbarWidth: 'thin', scrollbarColor: 'rgba(255,255,255,0.06) transparent' }}>
              <div className="p-6">
                {/* Now playing */}
                <div
                  className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-5 mb-4 cursor-pointer hover:bg-white/[0.05] transition-colors"
                  onClick={() => toggleExpand(currentStory.id)}
                >
                  <div className="flex items-center gap-2 mb-2 text-xs text-zinc-600 capitalize">
                    <span className="flex items-center gap-1.5 text-purple-400 font-bold tracking-[0.15em] normal-case">
                      <span className="w-2 h-2 rounded-full bg-purple-500 animate-pulse" />
                      NOW PLAYING
                    </span>
                    <span className="text-zinc-800">|</span>
                    <span>{depth.label.toLowerCase()}</span>
                    {currentStory.category.map((cat) => (
                      <span key={cat}><span className="text-zinc-800 mx-1">|</span>{cat.toLowerCase()}</span>
                    ))}
                  </div>
                  <h3 className="text-base font-semibold text-white leading-snug">
                    {currentStory.title}
                  </h3>
                  {expandedId === currentStory.id && (
                    <p className="mt-3 text-sm text-zinc-400 leading-relaxed">{currentStory.text}</p>
                  )}
                  <div className="flex justify-end mt-2">
                    {expandedId === currentStory.id
                      ? <ChevronUp className="w-4 h-4 text-zinc-700" />
                      : <ChevronDown className="w-4 h-4 text-zinc-700" />
                    }
                  </div>
                </div>

                {feedStories.length === 0 && (
                  <div className="py-16 text-center text-sm text-zinc-700">
                    No stories matching filter
                  </div>
                )}

                {feedStories.map((story) => {
                  const d = DEPTH_CONFIG[story.depth] || DEPTH_CONFIG.FLASH;
                  const time = format(new Date(story.published_at), 'HH:mm');
                  const isExpanded = expandedId === story.id;

                  return (
                    <div
                      key={story.id}
                      className="py-4 border-b border-white/[0.04] cursor-pointer hover:bg-white/[0.02] transition-colors rounded-lg px-3 -mx-3"
                      onClick={() => toggleExpand(story.id)}
                    >
                      <div className="flex items-center gap-2 mb-2 text-xs text-zinc-600 capitalize">
                        <span className="font-mono">{time}</span>
                        <span className="text-zinc-800">|</span>
                        <span>{d.label.toLowerCase()}</span>
                        {story.category.map((cat) => (
                          <span key={cat}><span className="text-zinc-800 mx-1">|</span>{cat.toLowerCase()}</span>
                        ))}
                      </div>
                      <h3 className="text-[15px] font-medium text-zinc-300 leading-snug">
                        {story.title}
                      </h3>
                      {isExpanded && (
                        <p className="mt-2.5 text-sm text-zinc-500 leading-relaxed">{story.text}</p>
                      )}
                      <div className="flex justify-end mt-2">
                        {isExpanded
                          ? <ChevronUp className="w-4 h-4 text-zinc-800" />
                          : <ChevronDown className="w-4 h-4 text-zinc-800" />
                        }
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
};

export default LivePage;
