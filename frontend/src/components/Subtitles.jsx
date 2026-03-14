import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Groups word-level subtitle entries into natural phrases.
 * Port of backend/core/producer/subtitle.py grouping logic.
 */
function groupIntoPhrases(words) {
  const phrases = [];
  let current = { text: [], start: null, end: null };

  for (let i = 0; i < words.length; i++) {
    const { text, start, end } = words[i];

    if (
      current.text.length &&
      ((start - current.end > 0.3) ||
       (current.text.join(' ').length > 30) ||
       /[.!?]$/.test(current.text[current.text.length - 1]))
    ) {
      phrases.push(current);
      current = { text: [text], start, end };
    } else {
      if (current.start === null) current.start = start;
      current.text.push(text);
      current.end = end;
    }

    if (i === words.length - 1 && current.text.length) {
      phrases.push(current);
    }
  }

  return phrases.map((p) => ({
    text: p.text.join(' ').replace(/ dot fm/g, '.fm'),
    start: p.start,
    end: p.end,
  }));
}

const Subtitles = ({ subtitleUrl, audioRef }) => {
  const [phrases, setPhrases] = useState([]);
  const [activeIndex, setActiveIndex] = useState(-1);
  const rafRef = useRef(null);

  // Fetch and parse subtitle JSON
  useEffect(() => {
    if (!subtitleUrl) return;
    setPhrases([]);
    setActiveIndex(-1);

    fetch(subtitleUrl)
      .then((r) => (r.ok ? r.json() : []))
      .then((words) => setPhrases(groupIntoPhrases(words)))
      .catch(() => {});
  }, [subtitleUrl]);

  // Sync active phrase to audio currentTime
  const sync = useCallback(() => {
    const audio = audioRef?.current;
    if (!audio || !phrases.length) {
      rafRef.current = requestAnimationFrame(sync);
      return;
    }

    if (audio.currentTime === 0) {
      setActiveIndex(-1);
      rafRef.current = requestAnimationFrame(sync);
      return;
    }

    const t = audio.currentTime;
    let idx = -1;
    for (let i = 0; i < phrases.length; i++) {
      if (t >= phrases[i].start && t <= phrases[i].end + 0.15) {
        idx = i;
        break;
      }
    }
    setActiveIndex(idx);
    rafRef.current = requestAnimationFrame(sync);
  }, [phrases, audioRef]);

  useEffect(() => {
    rafRef.current = requestAnimationFrame(sync);
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); };
  }, [sync]);

  if (!phrases.length || activeIndex < 0) return null;

  return (
    <div className="text-center px-8">
      <p className="text-[15px] text-zinc-300/90 font-medium leading-relaxed transition-opacity duration-200">
        {phrases[activeIndex].text}
      </p>
    </div>
  );
};

export default Subtitles;
