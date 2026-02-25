import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="login-container">
      <div class="login-box">
        <div class="logo">
          <i class="fas fa-chart-line"></i>
          <h1>Market Analyser</h1>
        </div>
        <p>Your institutional-grade market analysis suite.</p>
        
        <form (submit)="loginWithLocal($event)" class="local-login-form">
          <input type="email" [(ngModel)]="localEmail" name="email" placeholder="Email" required class="input-field" />
          <input type="password" [(ngModel)]="localPassword" name="password" placeholder="Password" required class="input-field" />
          <button type="submit" class="primary-btn" [disabled]="isLoading">
            {{ isLoading ? 'Signing In...' : 'Sign In' }}
          </button>
          @if (errorMessage) {
            <div class="error-msg">{{ errorMessage }}</div>
          }
        </form>

        <div class="divider"><span>OR</span></div>

        <button (click)="loginWithGoogle()" class="google-btn">
          <img src="https://upload.wikimedia.org/wikipedia/commons/c/c1/Google_'G'_logo.svg" alt="Google logo" />
          <span>Sign in with Google</span>
        </button>
        
        <div class="footer-note">
          By signing in, you agree to our terms of service and privacy policy. <br>
          <a href="#" (click)="toggleMode($event)">{{ isLoginMode ? 'Create an account' : 'Already have an account?' }}</a>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .login-container {
      height: 100vh;
      width: 100vw;
      display: flex;
      align-items: center;
      justify-content: center;
      background: radial-gradient(circle at top right, #1a1a2e, #16213e);
      color: white;
    }

    .login-box {
      background: rgba(255, 255, 255, 0.05);
      backdrop-filter: blur(10px);
      padding: 3rem;
      border-radius: 24px;
      text-align: center;
      max-width: 400px;
      width: 90%;
      border: 1px solid rgba(255, 255, 255, 0.1);
      box-shadow: 0 20px 40px rgba(0,0,0,0.4);
    }

    .logo {
      font-size: 3rem;
      color: #007bff;
      margin-bottom: 1rem;
      h1 {
        font-size: 2rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        margin-top: 0.5rem;
        background: linear-gradient(135deg, #007bff, #00d2ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
      }
    }

    p {
      color: #94a3b8;
      margin-bottom: 2.5rem;
      line-height: 1.6;
    }

    .google-btn {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 12px;
      width: 100%;
      padding: 0.8rem;
      background: white;
      color: #1e293b;
      border: none;
      border-radius: 12px;
      font-size: 1rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.3s ease;
      
      img {
        width: 20px;
        height: 20px;
      }

      &:hover {
        background: #f8fafc;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
      }
    }

    .local-login-form {
      display: flex;
      flex-direction: column;
      gap: 1rem;
      margin-bottom: 1.5rem;
    }

    .input-field {
      padding: 0.8rem 1rem;
      border-radius: 8px;
      border: 1px solid rgba(255, 255, 255, 0.2);
      background: rgba(0, 0, 0, 0.2);
      color: white;
      font-size: 1rem;
      
      &:focus {
        outline: none;
        border-color: #007bff;
        background: rgba(0, 0, 0, 0.4);
      }
    }

    .primary-btn {
      padding: 0.8rem;
      border-radius: 8px;
      border: none;
      background: #007bff;
      color: white;
      font-size: 1rem;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.3s;
    }

    .primary-btn:hover:not(:disabled) {
      background: #0056b3;
    }

    .primary-btn:disabled {
      opacity: 0.7;
      cursor: not-allowed;
    }

    .divider {
      display: flex;
      align-items: center;
      text-align: center;
      margin: 1.5rem 0;
      color: #64748b;
      
      &::before, &::after {
        content: '';
        flex: 1;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
      }
      
      span {
        padding: 0 10px;
        font-size: 0.85rem;
        font-weight: 600;
      }
    }

    .error-msg {
      color: #ef4444;
      font-size: 0.85rem;
      margin-top: 0.5rem;
    }

    .footer-note {
      margin-top: 2rem;
      font-size: 0.75rem;
      color: #64748b;
      
      a {
        color: #007bff;
        text-decoration: none;
        font-weight: 600;
        margin-top: 0.5rem;
        display: inline-block;
        
        &:hover {
          text-decoration: underline;
        }
      }
    }
  `]
})

export class LoginComponent {
  localEmail = '';
  localPassword = '';
  isLoading = false;
  errorMessage = '';
  isLoginMode = true; // true = login, false = register

  private http = inject(HttpClient);
  private authService = inject(AuthService);

  // Hardcoded for direct access during development
  private apiUrl = 'https://o9dgs1ujz1.execute-api.ap-southeast-1.amazonaws.com/api/auth';

  loginWithGoogle() {
    window.location.href = `${this.apiUrl}/login`;
  }

  toggleMode(event: Event) {
    event.preventDefault();
    this.isLoginMode = !this.isLoginMode;
    this.errorMessage = '';
  }

  loginWithLocal(event: Event) {
    event.preventDefault();
    if (!this.localEmail || !this.localPassword) {
      this.errorMessage = 'Email and password are required.';
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';

    if (this.isLoginMode) {
      this.http.post<any>(`${this.apiUrl}/local/login`, {
        email: this.localEmail,
        password: this.localPassword
      }).subscribe({
        next: (res) => {
          this.authService.setToken(res.access_token);
          this.authService.setUser(res.user);
          window.location.reload();
        },
        error: (err) => {
          this.errorMessage = err.error?.detail || 'Login failed. Please check credentials.';
          this.isLoading = false;
        }
      });
    } else {
      // Register Mode
      this.http.post<any>(`${this.apiUrl}/local/register`, {
        email: this.localEmail,
        password: this.localPassword,
        name: this.localEmail.split('@')[0]
      }).subscribe({
        next: () => {
          // Auto login after register
          this.isLoginMode = true;
          this.loginWithLocal(event);
        },
        error: (err) => {
          this.errorMessage = err.error?.detail || 'Registration failed. Email might exist.';
          this.isLoading = false;
        }
      });
    }
  }
}
