import { Component, EventEmitter, Output, OnInit, AfterViewInit } from '@angular/core';
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
    <!-- Debug info -->
    <div style="position: absolute; top: -100px; left: 0; font-size: 10px; color: red;">
      DEBUG: Theme toggle rendered
    </div>
  `,
  styleUrls: ['./theme-toggle.component.scss']
})
export class ThemeToggleComponent implements OnInit, AfterViewInit {
  @Output() themeChanged = new EventEmitter<'dark' | 'light'>();

  constructor(public themeService: ThemeService) {
    console.log('ThemeToggleComponent: Initialized');
  }

  ngOnInit() {
    console.log('ThemeToggleComponent: ngOnInit called');
  }

  ngAfterViewInit() {
    console.log('ThemeToggleComponent: ngAfterViewInit called - component should be visible');
  }

  toggleTheme(): void {
    console.log('ThemeToggleComponent: Toggle button clicked - method called');
    try {
      this.themeService.toggleTheme();
      this.themeChanged.emit(this.themeService.currentTheme());
      console.log('ThemeToggleComponent: Theme changed to:', this.themeService.currentTheme());
    } catch (error) {
      console.error('ThemeToggleComponent: Error during toggle:', error);
    }
  }

  getToggleTitle(): string {
    const currentTheme = this.themeService.currentTheme();
    return `Switch to ${currentTheme === 'dark' ? 'Light' : 'Dark'} Mode`;
  }
}
