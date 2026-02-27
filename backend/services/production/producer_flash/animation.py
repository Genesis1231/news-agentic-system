from config import logger
import numpy as np
from moviepy import VideoClip
from PIL import Image, ImageDraw
import librosa
from scipy.interpolate import interp1d

class ParticleSystem:
    def __init__(self, width: int, height: int, n_particles: int = 100):
        self.width = width
        self.height = height
        self.n_particles = n_particles
        self.center = np.array([width/2, height/2])
        
        # Initialize all particles at the center
        self.positions = np.tile(self.center, (n_particles, 1))
        
        # Initialize velocities with circular spread pattern
        angles = np.linspace(0, 2*np.pi, n_particles)
        self.velocities = np.column_stack([
            np.cos(angles),
            np.sin(angles)
        ]) * 2  # Initial velocity magnitude
        
        # Rest of initialization remains the same
        self.base_sizes = np.random.rand(n_particles) * 3 + 1
        self.sizes = self.base_sizes.copy()
        self.colors = np.ones((n_particles, 4))
        self.colors[:, 3] = 0.5
        
        # Multiple radius layers for more dynamic movement
        self.radius_multipliers = np.random.rand(n_particles) * 0.5 + 0.75
        
    def update(self, audio_intensity: float, frame_number: int):
        # Ensure non-negative intensity and scale it
        intensity_factor = audio_intensity * 3  # Linear scaling instead of power
        
        time = frame_number * 0.03  # Slower base movement
        
        # Ensure non-negative audio intensity
        safe_intensity = np.clip(audio_intensity, 0, None)  # Prevent negative values
        intensity_factor = np.power(safe_intensity, 0.5) * 3  # Now safe for power operation
        
        # Update particle behavior based on audio intensity
        for i in range(self.n_particles):
            # Smaller, more contained radius
            base_radius = 80 + (intensity_factor * 40)  # Reduced base and intensity impact
            radius = base_radius * self.radius_multipliers[i]
            
            # Varied movement patterns
            angle = time + (2 * np.pi * i / self.n_particles)
            if i % 3 == 0:  # Every third particle moves differently
                angle = time * 1.5 + (2 * np.pi * i / self.n_particles)
            
            # Calculate target position
            target = self.center + np.array([
                np.cos(angle) * radius,
                np.sin(angle) * radius * 1.2  # Slightly elongated vertically
            ])
            
            # Responsive movement
            dir_to_target = target - self.positions[i]
            self.velocities[i] += dir_to_target * (0.02 + (intensity_factor * 0.02))
            
            # Add randomness based on audio intensity
            self.velocities[i] += np.random.randn(2) * intensity_factor * 0.8
            
            # Update positions with increased responsiveness
            self.positions[i] += self.velocities[i] * (1 + intensity_factor * 0.5)
            
            # Strong damping for quick response to audio changes
            self.velocities[i] *= 0.85
            
            # Update sizes based on audio intensity
            self.sizes[i] = self.base_sizes[i] * (1 + intensity_factor)
            
            # Wrap around edges
            self.positions[i] %= [self.width, self.height]
        
        # Update colors with more dramatic changes
        self.colors[:, 0] = np.clip(0.4 + intensity_factor * 0.6, 0, 1)  # Red
        self.colors[:, 1] = np.clip(0.3 + intensity_factor * 0.3, 0, 1)  # Green
        self.colors[:, 2] = np.clip(0.7 + intensity_factor * 0.3, 0, 1)  # Blue
        self.colors[:, 3] = np.clip(0.2 + intensity_factor * 0.4, 0, 0.8)  # Alpha

    def draw(self):
        img = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        for i in range(self.n_particles):
            x, y = self.positions[i]
            size = self.sizes[i]
            # Ensure color values are within valid range before conversion
            safe_colors = np.clip(self.colors[i], 0, 1)  # Clip to valid range
            color_values = (safe_colors * 255).astype(int)
            color = tuple(color_values)
            
            draw.ellipse([x-size, y-size, x+size, y+size], fill=color)
            
        return np.array(img)

def create_particle_video(audio_path: str, duration: float) -> VideoClip:
    """Create a particle video from an audio file."""

    # Load audio with specific sample rate
    y, sr = librosa.load(audio_path, sr=22050, duration=duration)
    logger.debug(f"audio loaded, duration: {duration}, sample rate {sr}")
    
    # Optimize frame hop length for speech
    hop_length = 256  # Smaller hop length for more precise analysis
    
    # Adjusted frequency range for better mel filter coverage
    mel_spec = librosa.feature.melspectrogram(
        y=y, 
        sr=sr,
        n_mels=64,  # Reduced number of mel bands
        hop_length=hop_length,
        fmin=80,    # Lowest frequency of human voice
        fmax=8000,  # Cover full range of speech harmonics
        power=2.0   # Squared magnitude for better dynamics
    )
    
    # Get amplitude envelope and ensure non-negative values
    amplitude_envelope = np.abs(librosa.stft(y, hop_length=hop_length))
    amplitude_envelope = np.mean(amplitude_envelope, axis=0)
    amplitude_envelope = amplitude_envelope / (amplitude_envelope.max() + 1e-10)  # Prevent division by zero
    
    # Combine mel spectrogram and amplitude for better speech response
    mel_db = librosa.power_to_db(mel_spec, ref=np.max)
    intensity = np.mean(mel_db, axis=0)
    
    # Normalize intensity to [0, 1] range with safeguards
    intensity_min = np.min(intensity)
    intensity_max = np.max(intensity)
    if intensity_max > intensity_min:
        intensity = (intensity - intensity_min) / (intensity_max - intensity_min)
    else:
        intensity = np.zeros_like(intensity)
    
    # Combine with amplitude envelope for better response
    intensity = np.clip((intensity + amplitude_envelope) / 2, 0, 1)  # Ensure range [0, 1]
    
    # Smooth the intensity curve
    window_size = 3
    smoothing_window = np.hanning(window_size)
    smoothing_window = smoothing_window / np.sum(smoothing_window)
    intensity = np.convolve(intensity, smoothing_window, mode='same')
    
    # Create time array and interpolation
    times = librosa.times_like(intensity, sr=sr, hop_length=hop_length)
    get_intensity = interp1d(times, intensity, bounds_error=False, fill_value="extrapolate")
    
    # Initialize particle system
    particles = ParticleSystem(720, 1280, n_particles=150)
    
    def make_frame(t):
        current_intensity = float(get_intensity(t))
        particles.update(current_intensity, int(t * 30))
        return particles.draw()
    
    # Create video clip
    return VideoClip(make_frame, duration=duration)
    

