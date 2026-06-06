import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { AuthService } from './auth.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
    const authService = inject(AuthService);
    const token = authService.token();

    const handled = token
        ? next(req.clone({ setHeaders: { Authorization: `Bearer ${token}` } }))
        : next(req);

    return handled.pipe(
        catchError((error) => {
            // Token expired / invalid -> clear session and bounce back to the login page.
            if (error?.status === 401 && authService.token()) {
                authService.clearSession();
                window.location.reload();
            }
            return throwError(() => error);
        })
    );
};
