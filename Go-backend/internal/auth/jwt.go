package auth

import (
	"os"
	"time"

	"game-site-backend/internal/models"

	"github.com/golang-jwt/jwt/v5"
)

func GenerateToken(userID int, username string) (string, error) {
	secret := os.Getenv("JWT_SECRET")
	if secret == "" {
		secret = "default-dev-secret-key-in-production"
	}

	claims := models.Claims{
		UserId:   userID,
		Username: username,
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(time.Hour * 24)),

			IssuedAt: jwt.NewNumericDate(time.Now()),

			Issuer: "game-site-backend",
		},
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)

	tokenString, err := token.SignedString([]byte(secret))
	if err != nil {
		return "", err
	}

	return tokenString, nil
}
