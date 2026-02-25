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
    }

    get isLoggedIn(): boolean {
        return !!this.token();
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
        this.token.set(null);
        this.user.set(null);
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user');
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
