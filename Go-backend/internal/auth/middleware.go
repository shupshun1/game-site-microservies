package auth

import (
	"context"
	"net/http"
	"strings"
)

func AuthMiddleware(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		author := r.Header.Get("Authorization")
		if !strings.HasPrefix(author, "Bearer") {
			http.Error(w, "Unauthorized", http.StatusUnauthorized)
			return
		}

		token := author[7:]
		claims, err := ValidateToken(token)
		if err != nil {
			http.Error(w, "Unauthorized", http.StatusUnauthorized)
			return
		}

		ctx := context.WithValue(r.Context(), "user_id", claims.UserId)
		r = r.WithContext(ctx)
		next(w, r)
	}
}
