import { Link } from 'react-router-dom';
import { Mic, Newspaper, Cpu } from 'lucide-react';
import BurstLogo from '../components/BurstLogo';
import SubscribeForm from '../components/SubscribeForm';

const HomePage = () => {
  return (
    <div className="min-h-screen bg-black text-white selection:bg-purple-500 selection:text-white">
      {/* Subtle gradient background */}
      <div className="absolute inset-0 bg-gradient-to-b from-purple-900/10 to-black pointer-events-none" />

      {/* Floating orb effect */}
      <div className="absolute top-20 right-20 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-20 left-20 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="relative">
        {/* Navigation */}
        <nav className="container mx-auto py-8">
          <div className="max-w-5xl mx-auto px-8">
            <div className="flex items-center gap-3">
              <BurstLogo size={28} />
              <div className="flex items-baseline antialiased">
                <span className="text-2xl font-semibold tracking-tight text-white-100">burst.fm</span>
              </div>
            </div>
          </div>
        </nav>

        {/* Hero Section */}
        <div className="container mx-auto px-4 pt-24 pb-32">
          <div className="max-w-4xl mx-auto">
            <div className="space-y-6 text-center mb-16">
              <h1 className="text-6xl md:text-7xl font-light tracking-tight">
                The Emerging Voice in Tech
                <span className="block mt-2 bg-gradient-to-r from-purple-400 via-pink-500 to-purple-600 bg-clip-text text-transparent leading-tight pb-1 font-semibold">
                Pure Signal, Zero Noise.
                </span>
              </h1>
              <p className="text-xl md:text-2xl text-zinc-400 font-light tracking-wide max-w-2xl mx-auto">
              24/7 global tech news & AI insights, delivered in real-time.
              </p>
            </div>

            {/* Start Listening CTA */}
            <div className="flex justify-center">
              <Link
                to="/live"
                className="px-8 py-3.5 bg-blue-600 text-white rounded-xl font-medium text-lg hover:bg-blue-700 transition-all duration-200"
              >
                Start Listening
              </Link>
            </div>
          </div>
        </div>

        {/* Features Section */}
        <div className="container mx-auto py-32 border-t border-white/10">
          <div className="max-w-5xl mx-auto px-8">
            <div className="grid md:grid-cols-3 gap-12">
              {[
                {
                  icon: <Mic className="w-6 h-6" />,
                  title: "Instant Coverage",
                  description: "Real-time reporting and analysis of tech news across all time zones. Never miss a beat in the future of technology."
                },
                {
                  icon: <Cpu className="w-6 h-6" />,
                  title: "AI-Powered Insights",
                  description: "Uncover unique perspectives through AI. Understand emerging trends and shape your vision for tomorrow."
                },
                {
                  icon: <Newspaper className="w-6 h-6" />,
                  title: "Trustworthy News",
                  description: "Decode complex tech news from the most reliable sources. Cut through the noise and focus on what truly matters."
                }
              ].map((feature, index) => (
                <div key={index} className="flex flex-col p-8 bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 hover:border-purple-500/30 transition-all duration-300">
                  <div className="flex items-center space-x-4 mb-4">
                    <div className="text-purple-500">{feature.icon}</div>
                    <h3 className="text-xl font-light">{feature.title}</h3>
                  </div>
                  <p className="text-zinc-400 leading-relaxed">{feature.description}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Subscribe Section */}
        <div className="container mx-auto py-16 border-t border-white/10">
          <div className="max-w-md mx-auto text-center">
            <p className="text-sm text-zinc-500 font-light mb-6">Get notified when new features drop</p>
            <SubscribeForm />
          </div>
        </div>

        {/* Footer */}
        <footer className="container mx-auto px-4 py-8 text-center text-sm text-zinc-600 font-light">
          © 2026 Burst.fm. All rights reserved.
        </footer>
      </div>
    </div>
  );
};

export default HomePage;
