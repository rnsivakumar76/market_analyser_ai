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
    const newTheme = this.themeService.currentTheme() === 'dark' ? 'light' : 'dark';
    this.themeService.setTheme(newTheme);
    this.themeChanged.emit(newTheme);
  }

  getThemeIcon(): string {
    return this.themeService.currentTheme() === 'dark' ? '🌙' : '☀️';
  }

  getThemeLabel(): string {
    return this.themeService.currentTheme() === 'dark' ? 'DARK' : 'LIGHT';
  }

  getToggleTitle(): string {
    return `Switch to ${this.themeService.currentTheme() === 'dark' ? 'Light' : 'Dark'} Mode`;
  }
}
