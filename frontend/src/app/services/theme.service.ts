import { Injectable, signal } from '@angular/core';

export type Theme = 'dark' | 'light';

@Injectable({
  providedIn: 'root'
})
export class ThemeService {
  private readonly THEME_KEY = 'market-analyzer-theme';
  
  currentTheme = signal<Theme>('dark');
  
  constructor() {
    this.initializeTheme();
  }
  
  private initializeTheme(): void {
    console.log('ThemeService: Initializing theme...');
    
    // Check for saved theme preference
    const savedTheme = localStorage.getItem(this.THEME_KEY) as Theme;
    console.log('ThemeService: Saved theme:', savedTheme);
    
    if (savedTheme && (savedTheme === 'dark' || savedTheme === 'light')) {
      this.currentTheme.set(savedTheme);
      console.log('ThemeService: Using saved theme:', savedTheme);
    } else {
      // Check system preference
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      const systemTheme = prefersDark ? 'dark' : 'light';
      this.currentTheme.set(systemTheme);
      console.log('ThemeService: Using system theme:', systemTheme, 'prefersDark:', prefersDark);
    }
    
    this.applyTheme(this.currentTheme());
    console.log('ThemeService: Theme initialized to:', this.currentTheme());
  }
  
  toggleTheme(): void {
    const currentTheme = this.currentTheme();
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    console.log('ThemeService: Toggling theme from', currentTheme, 'to', newTheme);
    this.setTheme(newTheme);
  }
  
  setTheme(theme: Theme): void {
    this.currentTheme.set(theme);
    localStorage.setItem(this.THEME_KEY, theme);
    this.applyTheme(theme);
  }
  
  private applyTheme(theme: Theme): void {
    console.log('ThemeService: Applying theme:', theme);
    const root = document.documentElement;
    
    // Remove existing theme classes
    root.classList.remove('light-theme', 'dark-theme');
    
    if (theme === 'light') {
      root.classList.add('light-theme');
      console.log('ThemeService: Added light-theme class');
    } else {
      root.classList.add('dark-theme');
      console.log('ThemeService: Added dark-theme class');
    }
    
    console.log('ThemeService: Current root classes:', root.className);
    
    // Update meta theme-color for mobile browsers
    const themeColor = theme === 'light' ? '#ffffff' : '#11111b';
    const metaThemeColor = document.querySelector('meta[name="theme-color"]');
    if (metaThemeColor) {
      metaThemeColor.setAttribute('content', themeColor);
      console.log('ThemeService: Updated meta theme-color to:', themeColor);
    }
  }
  
  getThemeIcon(): string {
    return this.currentTheme() === 'dark' ? '🌙' : '☀️';
  }
  
  getThemeLabel(): string {
    return this.currentTheme() === 'dark' ? 'Dark' : 'Light';
  }
}
