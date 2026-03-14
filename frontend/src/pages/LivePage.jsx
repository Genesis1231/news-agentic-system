import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import { Play, Pause, ChevronDown, ChevronUp, Volume2, VolumeX } from 'lucide-react';
import { format } from 'date-fns';
import BurstLogo from '../components/BurstLogo';
import AudioParticles from '../components/AudioParticles';
import { MOCK_STORIES, CATEGORIES, DEPTH_CONFIG } from '../data/mockStories';

const CATEGORY_KEYS = new Set(CATEGORIES.map((c) => c.key));

const ALL_TAGS = [
  ...CATEGORIES.map((c) => ({ label: c.label, value: c.key })),
  ...[...new Set(MOCK_STORIES.flatMap((s) => s.entities))].sort().map((e) => ({
    label: e,
    value: e,
  })),
];

const LivePage = () => {
  const [isPlaying, setIsPlaying] = useState(true); // autoplay
  const [currentIndex, setCurrentIndex] = useState(0);
  const [progress, setProgress] = useState(0);
  const [isMuted, setIsMuted] = useState(false);
  const [activeFilter, setActiveFilter] = useState('ALL');
  const [expandedId, setExpandedId] = useState(MOCK_STORIES[0].id);
  const [filtersExpanded, setFiltersExpanded] = useState(false);
  const [audioError, setAudioError] = useState(false);
  const audioRef = useRef(null);

  const currentStory = MOCK_STORIES[currentIndex];
  const depth = DEPTH_CONFIG[currentStory.depth] || DEPTH_CONFIG.FLASH;

  // Play/pause audio
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    if (isPlaying) {
      audio.play().catch(() => {
        // Browser blocked autoplay — switch to paused state
        setIsPlaying(false);
      });
    } else {
      audio.pause();
    }
  }, [isPlaying]);

  // Mute/unmute — set imperatively since React doesn't reliably update audio attributes
  useEffect(() => {
    const audio = audioRef.current;
    if (audio) audio.muted = isMuted;
  }, [isMuted, currentIndex]);

  // Update audio src when track changes
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.src = currentStory.audio_url;
    audio.load();
    setProgress(0);
    setAudioError(false);
    if (isPlaying) {
      audio.play().catch(() => {});
    }
  }, [currentIndex]);

  // Audio events
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const onTimeUpdate = () => {
      if (audio.duration && isFinite(audio.duration)) {
        setProgress((audio.currentTime / audio.duration) * 100);
      }
    };

    const onEnded = () => {
      const next = (currentIndex + 1) % MOCK_STORIES.length;
      setCurrentIndex(next);
      setExpandedId(MOCK_STORIES[next].id);
    };

    const onError = () => setAudioError(true);
    const onPlaying = () => setAudioError(false);

    audio.addEventListener('timeupdate', onTimeUpdate);
    audio.addEventListener('ended', onEnded);
    audio.addEventListener('error', onError);
    audio.addEventListener('playing', onPlaying);
    return () => {
      audio.removeEventListener('timeupdate', onTimeUpdate);
      audio.removeEventListener('ended', onEnded);
      audio.removeEventListener('error', onError);
      audio.removeEventListener('playing', onPlaying);
    };
  }, [currentIndex]);

  const toggleExpand = useCallback((id) => {
    setExpandedId((prev) => (prev === id ? null : id));
  }, []);

  const feedStories = useMemo(() => {
    const rest = MOCK_STORIES.filter((s) => s.id !== currentStory.id);
    if (activeFilter === 'ALL') return rest;
    if (CATEGORY_KEYS.has(activeFilter)) return rest.filter((s) => s.category.includes(activeFilter));
    return rest.filter((s) => s.entities.includes(activeFilter));
  }, [activeFilter, currentStory.id]);

  const isLive = isPlaying && !audioError;

  return (
    <div className="h-screen bg-black text-white flex flex-col overflow-hidden">
      <audio ref={audioRef} src={MOCK_STORIES[0].audio_url} preload="auto" muted={isMuted} crossOrigin="anonymous" />

      <nav className="shrink-0 border-b border-white/[0.06] bg-black/60 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-8 py-6 flex items-center justify-between">
          <div className="flex items-center gap-5">
            <Link to="/" className="flex items-center gap-3 group">
              <BurstLogo size={28} />
              <span className="text-2xl font-semibold tracking-tight text-white/90 group-hover:text-white transition-colors">
                burst.fm
              </span>
            </Link>
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full border ${
              isLive
                ? 'border-red-500/20 bg-red-500/[0.06]'
                : 'border-zinc-600/30 bg-zinc-600/[0.06]'
            }`}>
              <span className="relative flex h-2 w-2">
                {isLive && (
                  <span className="absolute inset-0 rounded-full bg-red-500" style={{ animation: 'pulse-ring 1.5s ease-out infinite' }} />
                )}
                <span className={`relative rounded-full h-2 w-2 ${isLive ? 'bg-red-500' : 'bg-zinc-500'}`} />
              </span>
              <span className={`text-[11px] font-bold tracking-[0.25em] uppercase ${isLive ? 'text-red-400' : 'text-zinc-500'}`}>
                {isLive ? 'On Air' : 'Off Air'}
              </span>
            </div>
          </div>
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
          {isLive && <span className="absolute inset-0 rounded-full bg-red-500" style={{ animation: 'pulse-ring 1.5s ease-out infinite' }} />}
          <span className={`relative rounded-full h-2 w-2 ${isLive ? 'bg-red-500' : 'bg-zinc-500'}`} />
        </span>
      </div>

      {/* 50/50 split */}
      <div className="flex-1 min-h-0 flex justify-center">
        <div className="w-full max-w-7xl flex min-h-0">

          {/* LEFT: RADIO */}
          <aside className="hidden md:flex w-1/2 shrink-0 flex-col relative overflow-hidden">
            <AudioParticles isPlaying={isPlaying} audioRef={audioRef} />

            {/* Controls + title */}
            <div className="relative z-10 mt-auto px-10 pb-[18%]">
              {/* Slim play bar */}
              <div className="flex items-center gap-3 mb-5">
                <button
                  onClick={() => setIsPlaying((p) => !p)}
                  className="w-9 h-9 rounded-full bg-white/[0.08] border border-white/[0.12] flex items-center justify-center hover:bg-white/[0.14] transition-all active:scale-95 shrink-0"
                >
                  {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 ml-0.5" />}
                </button>
                <div className="flex-1 h-1 bg-white/[0.08] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-purple-500/50 rounded-full transition-all duration-100"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <button
                  onClick={() => setIsMuted((m) => !m)}
                  className="hover:text-zinc-400 transition-colors shrink-0"
                >
                  {isMuted
                    ? <VolumeX className="w-4 h-4 text-zinc-600" />
                    : <Volume2 className="w-4 h-4 text-zinc-600" />
                  }
                </button>
              </div>

              {/* Now playing info */}
              <div className="flex items-center gap-2.5 mb-3">
                <span className="px-2.5 py-1 rounded text-xs font-bold tracking-wider uppercase bg-purple-500/10 text-purple-400 border border-purple-500/20">
                  {currentStory.category[0]}
                </span>
                <span className={`flex items-center gap-1.5 text-xs font-bold tracking-wider uppercase ${depth.color}`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${depth.dot}`} />
                  {depth.label}
                </span>
              </div>
              <h2 className="text-2xl font-semibold leading-snug">
                {currentStory.title}
              </h2>
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
