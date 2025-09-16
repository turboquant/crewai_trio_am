#!/usr/bin/env python3
"""
Simple Thinking Wheel/Spinner for LLM Processing
Lightweight, no external dependencies, cross-platform
"""

import threading
import time
import sys
import itertools

class ThinkingWheel:
    """Simple animated spinner to show LLM processing"""
    
    def __init__(self, message="🤖 Thinking", style="dots"):
        self.message = message
        self.is_running = False
        self.thread = None
        
        # Different spinner styles
        self.styles = {
            "dots": ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],
            "bounce": ["⠁", "⠂", "⠄", "⠂"],
            "clock": ["🕐", "🕑", "🕒", "🕓", "🕔", "🕕", "🕖", "🕗", "🕘", "🕙", "🕚", "🕛"],
            "arrow": ["↑", "↗", "→", "↘", "↓", "↙", "←", "↖"],
            "simple": ["|", "/", "-", "\\"],
            "brain": ["🧠💭", "🤔💭", "💭🧠", "💭🤔"],
            "gears": ["⚙️ ", "⚙️⚙️", "⚙️⚙️⚙️", "⚙️⚙️"],
        }
        
        self.spinner_chars = self.styles.get(style, self.styles["dots"])
        self.spinner = itertools.cycle(self.spinner_chars)
    
    def _spin(self):
        """Run the spinner animation"""
        while self.is_running:
            char = next(self.spinner)
            # Clear line and write spinner
            sys.stdout.write(f"\r{self.message} {char}")
            sys.stdout.flush()
            time.sleep(0.1)
    
    def start(self):
        """Start the spinner"""
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self._spin)
            self.thread.daemon = True
            self.thread.start()
    
    def stop(self, completion_message=None):
        """Stop the spinner and optionally show completion message"""
        if self.is_running:
            self.is_running = False
            if self.thread:
                self.thread.join(timeout=0.2)
            
            # Clear the spinner line
            sys.stdout.write(f"\r{' ' * (len(self.message) + 10)}\r")
            
            # Show completion message if provided
            if completion_message:
                sys.stdout.write(f"{completion_message}\n")
            
            sys.stdout.flush()
    
    def update_message(self, new_message):
        """Update the spinner message"""
        self.message = new_message

# Context manager for easy use
class ThinkingContext:
    """Context manager for spinner - automatically starts/stops"""
    
    def __init__(self, message="🤖 Processing", style="dots", completion_message=None):
        self.spinner = ThinkingWheel(message, style)
        self.completion_message = completion_message
    
    def __enter__(self):
        self.spinner.start()
        return self.spinner
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            # Success
            completion = self.completion_message or "✅ Complete!"
        else:
            # Error occurred
            completion = "❌ Error occurred"
        
        self.spinner.stop(completion)

# Utility functions for common use cases
def thinking_wheel(func):
    """Decorator to add spinner to any function"""
    def wrapper(*args, **kwargs):
        message = kwargs.pop('thinking_message', '🤖 Processing')
        style = kwargs.pop('thinking_style', 'dots')
        
        with ThinkingContext(message, style):
            return func(*args, **kwargs)
    return wrapper

# Quick test function
def demo_spinners():
    """Demonstrate different spinner styles"""
    styles = ["dots", "clock", "arrow", "simple", "brain", "gears"]
    
    for style in styles:
        print(f"\n🎯 Testing '{style}' spinner...")
        
        with ThinkingContext(f"🤖 LLM analyzing data", style, f"✅ {style.title()} style complete!"):
            time.sleep(2)
        
        time.sleep(0.5)

if __name__ == "__main__":
    print("🎡 Thinking Wheel Demo")
    print("=" * 40)
    
    # Demo all styles
    demo_spinners()
    
    print("\n🎯 Testing context manager...")
    
    # Context manager example
    with ThinkingContext("🤖 Ollama generating response", "brain", "✅ Response generated!"):
        time.sleep(3)
    
    print("\n🎯 Testing manual control...")
    
    # Manual control example  
    spinner = ThinkingWheel("🤖 CrewAI agents collaborating", "gears")
    spinner.start()
    time.sleep(2)
    
    spinner.update_message("🤖 Finalizing report")
    time.sleep(1)
    
    spinner.stop("✅ Multi-agent analysis complete!")
    
    print("\n🎉 Demo complete!")
