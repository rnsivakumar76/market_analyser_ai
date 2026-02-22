import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="login-container">
      <div class="login-box">
        <div class="logo">
          <i class="fas fa-chart-line"></i>
          <h1>Market Analyser</h1>
        </div>
        <p>Your institutional-grade market analysis suite.</p>
        
        <button (click)="loginWithGoogle()" class="google-btn">
          <img src="https://upload.wikimedia.org/wikipedia/commons/c/c1/Google_'G'_logo.svg" alt="Google logo" />
          <span>Sign in with Google</span>
        </button>
        
        <div class="footer-note">
          By signing in, you agree to our terms of service and privacy policy.
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

    .footer-note {
      margin-top: 2rem;
      font-size: 0.75rem;
      color: #64748b;
    }
  `]
})
export class LoginComponent {
  loginWithGoogle() {
    // Redirect to backend login route which will handle the Google redirect
    window.location.href = 'https://o9dgs1ujz1.execute-api.ap-southeast-1.amazonaws.com/api/auth/login';
  }
}
