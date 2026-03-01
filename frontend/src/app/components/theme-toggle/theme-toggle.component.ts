import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ThemeService } from '../../services/theme.service';

@Component({
  selector: 'app-theme-toggle',
  standalone: true,
  imports: [CommonModule],
  template: `
    <button class="theme-toggle-btn" (click)="toggleTheme()" [title]="getToggleTitle()">
      <span class="theme-icon">{{ getThemeIcon() }}</span>
      <span class="theme-label">{{ getThemeLabel() }}</span>
    </button>
  `,
  styleUrls: ['./theme-toggle.component.scss']
})
export class ThemeToggleComponent {
  @Output() themeChanged = new EventEmitter<'dark' | 'light'>();

  constructor(public themeService: ThemeService) {
    console.log('ThemeToggleComponent: Initialized');
  }

  toggleTheme(): void {
    console.log('ThemeToggleComponent: Toggle button clicked');
    try {
      // Direct theme toggle
      const currentTheme = this.themeService.currentTheme();
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      
      console.log('ThemeToggleComponent: Switching from', currentTheme, 'to', newTheme);
      
      // Apply theme directly
      this.applyThemeDirectly(newTheme);
      
      // Update service
      this.themeService.setTheme(newTheme);
      
      // Emit change
      this.themeChanged.emit(newTheme);
      
      console.log('ThemeToggleComponent: Theme changed to:', newTheme);
    } catch (error) {
      console.error('ThemeToggleComponent: Error during toggle:', error);
    }
  }

  private applyThemeDirectly(theme: 'dark' | 'light'): void {
    const root = document.documentElement;
    
    // Remove existing theme classes
    root.classList.remove('light-theme', 'dark-theme');
    
    // Add new theme class
    if (theme === 'light') {
      root.classList.add('light-theme');
    } else {
      root.classList.add('dark-theme');
    }
    
    console.log('ThemeToggleComponent: Applied theme class', theme + '-theme');
    console.log('ThemeToggleComponent: Root classes now:', root.className);
  }

  getThemeIcon(): string {
    const currentTheme = this.themeService.currentTheme();
    return currentTheme === 'dark' ? '🌙' : '☀️';
  }

  getThemeLabel(): string {
    const currentTheme = this.themeService.currentTheme();
    return currentTheme === 'dark' ? 'DARK' : 'LIGHT';
  }

  getToggleTitle(): string {
    const currentTheme = this.themeService.currentTheme();
    return `Switch to ${currentTheme === 'dark' ? 'Light' : 'Dark'} Mode`;
  }
}
