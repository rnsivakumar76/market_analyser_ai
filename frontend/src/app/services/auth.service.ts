import { Injectable, signal, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { environment } from '../../environments/environment';

export interface User {
    id: string;
    email: string;
    name: string;
    picture: string;
}

@Injectable({
    providedIn: 'root'
})
export class AuthService {
    private http = inject(HttpClient);
    // Use dynamic environment URL
    private apiUrl = `${environment.apiUrl}/auth`;

    user = signal<User | null>(null);
    token = signal<string | null>(localStorage.getItem('auth_token'));

    constructor() {
        const savedUser = localStorage.getItem('user');
        if (savedUser) {
            this.user.set(JSON.parse(savedUser));
        }
        // Drop any stale/expired token on startup so the login page is shown immediately.
        const token = this.token();
        if (token && this.isTokenExpired(token)) {
            this.clearSession();
        }
    }

    get isLoggedIn(): boolean {
        const token = this.token();
        return !!token && !this.isTokenExpired(token);
    }

    /** Returns true if the JWT is missing an exp claim or has already expired. */
    private isTokenExpired(token: string): boolean {
        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            if (!payload?.exp) return false; // no exp claim -> treat as non-expiring
            // 10s leeway to avoid edge-of-expiry flapping
            return payload.exp * 1000 < Date.now() - 10_000;
        } catch {
            return true; // malformed token -> force re-login
        }
    }

    /** Clears auth state from memory + localStorage without reloading. */
    clearSession() {
        this.token.set(null);
        this.user.set(null);
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user');
    }

    setToken(token: string) {
        this.token.set(token);
        localStorage.setItem('auth_token', token);
    }

    setUser(user: User) {
        this.user.set(user);
        localStorage.setItem('user', JSON.stringify(user));
    }

    logout() {
        this.clearSession();
        window.location.reload(); // Refresh to clear state
    }

    handleGoogleCallback(code: string): Observable<any> {
        return this.http.get(`${this.apiUrl}/callback?code=${code}`).pipe(
            tap((res: any) => {
                this.setToken(res.access_token);
                this.setUser(res.user);
            })
        );
    }
}
