import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ThemeService } from '../../services/theme.service';

@Component({
  selector: 'app-theme-toggle',
  standalone: true,
  imports: [CommonModule],
  template: `
    <button class="theme-toggle-btn" (click)="toggleTheme()" [title]="getToggleTitle()">
      <span class="theme-icon">{{ themeService.getThemeIcon() }}</span>
      <span class="theme-label">{{ themeService.getThemeLabel() }}</span>
    </button>
  `,
  styleUrls: ['./theme-toggle.component.scss']
})
export class ThemeToggleComponent {
  @Output() themeChanged = new EventEmitter<'dark' | 'light'>();

  constructor(public themeService: ThemeService) {}

  toggleTheme(): void {
    this.themeService.toggleTheme();
    this.themeChanged.emit(this.themeService.currentTheme());
  }

  getToggleTitle(): string {
    const currentTheme = this.themeService.currentTheme();
    return `Switch to ${currentTheme === 'dark' ? 'Light' : 'Dark'} Mode`;
  }
}
