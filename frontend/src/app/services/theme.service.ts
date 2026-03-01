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
    // Check for saved theme preference
    const savedTheme = localStorage.getItem(this.THEME_KEY) as Theme;
    if (savedTheme && (savedTheme === 'dark' || savedTheme === 'light')) {
      this.currentTheme.set(savedTheme);
    } else {
      // Check system preference
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      this.currentTheme.set(prefersDark ? 'dark' : 'light');
    }
    
    this.applyTheme(this.currentTheme());
  }
  
  toggleTheme(): void {
    const newTheme = this.currentTheme() === 'dark' ? 'light' : 'dark';
    this.setTheme(newTheme);
  }
  
  setTheme(theme: Theme): void {
    this.currentTheme.set(theme);
    localStorage.setItem(this.THEME_KEY, theme);
    this.applyTheme(theme);
  }
  
  private applyTheme(theme: Theme): void {
    const root = document.documentElement;
    
    if (theme === 'light') {
      root.classList.add('light-theme');
      root.classList.remove('dark-theme');
    } else {
      root.classList.add('dark-theme');
      root.classList.remove('light-theme');
    }
    
    // Update meta theme-color for mobile browsers
    const themeColor = theme === 'light' ? '#ffffff' : '#11111b';
    const metaThemeColor = document.querySelector('meta[name="theme-color"]');
    if (metaThemeColor) {
      metaThemeColor.setAttribute('content', themeColor);
    }
  }
  
  getThemeIcon(): string {
    return this.currentTheme() === 'dark' ? '🌙' : '☀️';
  }
  
  getThemeLabel(): string {
    return this.currentTheme() === 'dark' ? 'Dark' : 'Light';
  }
}
