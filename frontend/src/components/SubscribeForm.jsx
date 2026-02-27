import React, { useState, useEffect } from 'react';
import { Loader2 } from 'lucide-react';

const SubscribeForm = () => {
  const [email, setEmail] = useState('');
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');
  const [displayedText, setDisplayedText] = useState('');

  useEffect(() => {
    if (isSubmitted && statusMessage) {
      // Clear any previous text and reset states
      setDisplayedText('');
      
      // Add a delay before starting the animation to ensure component is fully rendered
      const startDelay = setTimeout(() => {
        let currentIndex = 0;
        const typingInterval = setInterval(() => {
          if (currentIndex < statusMessage.length) {
            setDisplayedText(statusMessage.substring(0, currentIndex + 1));
            currentIndex++;
          } else {
            clearInterval(typingInterval);
          }
        }, 20);
        
        return () => clearInterval(typingInterval);
      }, 300); // Delay before starting animation
      
      return () => clearTimeout(startDelay);
    }
  }, [isSubmitted, statusMessage]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Local validation
    if (!email) {
      setError('Please enter your email address');
      return;
    }
    
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setError('Please enter a valid email address');
      return;
    }
    
    setError('');
    setIsLoading(true);
    
    // API endpoint
    const ENDPOINT = 'https://burst-api.burstfm.workers.dev/api/subscribe';

    try {
      const response = await fetch(ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error || 'Failed to subscribe. Please try again later.');
      }
      
      // Handle various success scenarios
      if (data.status === 'existing') {
        setStatusMessage("You are already on our list! Thanks for your enthusiasm.");
      } else {
        setStatusMessage("You are on the list. Welcome to the future of tech news!");
      }
      
      setIsSubmitted(true);
    } catch (err) {
      console.error('Subscription error:', err);
      setError(err.message || 'Something went wrong. Please try again later.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto">
      {isSubmitted ? (
        <div className="w-full h-[60px] flex items-center mb-6">
          <div className="w-full flex justify-center items-center">
            <div className="inline-flex items-center px-4">
              <p className="text-xl font-normal text-white whitespace-nowrap">
                {displayedText}
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div className="relative pb-6">
          <form onSubmit={handleSubmit} className="relative" noValidate>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email"
              aria-label="Email address"
              className="w-full px-6 py-4 bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 focus:outline-none focus:border-purple-500/50 transition-all duration-300 pr-36"
              disabled={isLoading}
            />
            <button
              type="submit"
              className="absolute right-2 top-2 bottom-2 px-6 bg-blue-500 text-white rounded-xl font-normal hover:bg-blue-600 transition-all duration-300 disabled:bg-blue-500/70 disabled:cursor-not-allowed flex items-center justify-center"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                "Get Early Access"
              )}
            </button>
          </form>
          {error && (
            <div className="bg-black/70 backdrop-blur-sm px-4 py-2 rounded-lg absolute left-0 mt-1">
              <p className="text-red-500 text-sm">{error}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SubscribeForm;
